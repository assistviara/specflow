import json
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from application.correction_cycle import CorrectionAttempt, CorrectionHistory, CorrectionCycleOutput, CycleFailure
from application.correction_cycle_validation import validate_cycle
from application.implementation_evidence_comparator import ImplementationEvidenceComparator
from application.correction_cycle_artifacts import snapshot_artifacts
from application.correction_cycle_prompt import build_cycle_prompt, history_context
from application.current_state_repository import load_current_state
from application.state_transition import transition_state
from application.implementation_result_parser import ImplementationResultParser
from application.dto import CollectImplementationEvidenceInput
from application.collect_implementation_evidence import CollectImplementationEvidenceUseCase
from application.prepare_review_input import PrepareReviewInputUseCase
from application.review_with_retry import ReviewWithRetryUseCase
from application.review_retry import RetryAuthorization


class ExecuteCorrectionCycleUseCase:
    def __init__(self, *, adapter, recorder, evidence_repository, repository_state_provider,
                 approval_repository, test_state_provider_factory, ai_service, snapshot=snapshot_artifacts,
                 retry_authorize=None):
        self._adapter = adapter
        self._recorder = recorder
        self._evidence_repository = evidence_repository
        self._repository = repository_state_provider
        self._approvals = approval_repository
        self._test_provider = test_state_provider_factory
        self._ai = ai_service
        self._snapshot = snapshot
        self._retry_authorize = retry_authorize or (lambda operation, failure: RetryAuthorization())

    def _transition(self, request, state, reason):
        current = load_current_state(request.state_file)['status']
        transition_state(request.state_file, request.state_history_dir, {
            'transition_id': str(uuid4()), 'from_state': current, 'to_state': state,
            'occurred_at': datetime.now().astimezone().isoformat(), 'reason': reason,
        })

    def execute(self, request):
        try:
            state = load_current_state(request.state_file)['status']
            failures = validate_cycle(request, state, self._evidence_repository, self._approvals)
        except Exception as error:
            return CorrectionCycleOutput(request, None, None, failures=(CycleFailure('start_condition', str(error)),))
        if failures:
            return CorrectionCycleOutput(request, None, state, failures=failures)
        routing = request.routing
        previous = routing.request.review.review.prepared.review_input
        source_paths = previous.request.source_paths if request.source_paths is None else request.source_paths
        test_paths = previous.request.test_paths if request.test_paths is None else request.test_paths
        old = previous.evidence
        identity = uuid4()
        count = routing.request.control.correction_count
        history = CorrectionHistory(identity, routing, old.identity.evidence_id, count, count)
        root = previous.request.repository_path
        request.artifact_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = request.artifact_dir / f'correction_prompts_{identity}.json'
        history_path = request.artifact_dir / f'correction_history_{identity}.json'
        bundle = {'implementation_id': str(identity), 'requests': []}
        failures = []
        evidence = prepared = reviewed = None

        def observe():
            values = self._snapshot(root)
            return {key: value for key, value in values.items()
                    if not (root / key).resolve().is_relative_to(request.artifact_dir.resolve())
                    and not (root / key).resolve().is_relative_to(request.state_history_dir.resolve())
                    and (root / key).resolve() != request.state_file.resolve()}

        def save_bundle():
            with bundle_path.open('x', encoding='utf-8', newline='\n') as stream:
                json.dump(bundle, stream, ensure_ascii=False, indent=2)

        def finish():
            nonlocal history
            history = replace(history, failures=tuple(failures))
            try:
                with history_path.open('x', encoding='utf-8', newline='\n') as stream:
                    json.dump({'history': asdict(history), 're_review': asdict(reviewed) if reviewed else None},
                              stream, default=str, ensure_ascii=False, indent=2)
            except Exception as error:
                failures.append(CycleFailure('history_persistence', str(error)))
                history = replace(history, failures=tuple(failures))
            return CorrectionCycleOutput(request, history, load_current_state(request.state_file)['status'],
                                         history_path, evidence, prepared, reviewed, tuple(failures))

        try:
            before = observe()
        except Exception as error:
            failures.append(CycleFailure('artifact_observation', str(error)))
            return finish()
        events = []
        self._transition(request, 'implementing', 'Correction Cycle started')

        def run(context):
            path = request.artifact_dir / f'correction_prompt_{identity}_{len(bundle["requests"])}.md'
            try:
                prompt = build_cycle_prompt(previous.codex_prompt.content, context)
                with path.open('x', encoding='utf-8', newline='\n') as stream:
                    stream.write(prompt)
                bundle['requests'].append({'path': str(path), 'prompt': prompt, 'operation': context['operation']})
                result = self._adapter.run(prompt=prompt, working_directory=root)
                for event in result.command_events:
                    events.append(replace(event, event_order=len(events) + 1))
                if not result.process_succeeded:
                    try:
                        parsed = ImplementationResultParser.parse(result.final_message or '')
                    except ValueError:
                        parsed = None
                    return path, parsed, CycleFailure('codex_execution', '; '.join(result.errors) or 'Codex process failed')
                parsed = ImplementationResultParser.parse(result.final_message or '')
                if parsed.human_approval_required.strip() != 'NONE':
                    return path, parsed, CycleFailure('scope_violation', parsed.human_approval_required)
                if parsed.incomplete_items.strip() != 'NONE':
                    return path, parsed, CycleFailure('codex_execution', parsed.incomplete_items)
                return path, parsed, None
            except Exception as error:
                return path, None, CycleFailure('codex_execution', f'{type(error).__name__}: {error}')

        for index, instruction in enumerate(routing.instructions):
            context = history_context(history, request.tests) | {
                'operation': 'CORRECTION', 'instruction_index': index,
                'instruction': asdict(instruction), 'cycle_number': count + 1,
            }
            path, parsed, failure = run(context)
            execution_failure = failure
            if execution_failure:
                failures.append(execution_failure)
            observed = None
            changes = ()
            try:
                after = observe()
                changes = tuple(sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key)))
                before = after
                observed = self._repository.get_state(old.identity.base_commit)
                protected = (old.basis.specification_path, old.basis.implementation_plan_path, old.basis.codex_prompt_path)
                forbidden = [name for name in changes if (root / name).resolve() in {p.resolve() for p in protected}
                    or not ImplementationEvidenceComparator._matches_any(name, old.scope.target_paths)
                    or not ImplementationEvidenceComparator._matches_any(name, old.scope.allowed_changes)
                    or ImplementationEvidenceComparator._matches_any(name, old.scope.forbidden_changes)]
                if forbidden:
                    failure = CycleFailure('scope_violation', ', '.join(forbidden))
            except Exception as error:
                failure = CycleFailure('artifact_observation', str(error))
            attempt = CorrectionAttempt(index, path, parsed.implementation_summary if parsed else None, changes, observed, failure, parsed)
            history = replace(history, attempts=(*history.attempts, attempt),
                              changed_files=tuple(sorted(set(history.changed_files) | set(changes))))
            if failure:
                if failure != execution_failure:
                    failures.append(failure)
                break

        history = replace(history, correction_count=count + bool(history.changed_files))
        if not history.changed_files:
            failures.append(CycleFailure('artifact_change_not_established', 'No cycle artifact change was confirmed'))
        if failures:
            self._transition(request, 'implementation_failed', 'Correction operation failed')
        else:
            self._transition(request, 'implementation_completed', 'Correction operations completed')
            _, parsed, test_failure = run(history_context(history, request.tests) | {
                'operation': 'RE_TEST_ONLY', 'test_commands': request.tests.commands(),
            })
            history = replace(history, retest_result=parsed)
            if test_failure:
                failures.append(CycleFailure('test_execution_error', test_failure.detail))
            try:
                after_tests = observe()
                changes = tuple(sorted(key for key in before.keys() | after_tests.keys() if before.get(key) != after_tests.get(key)))
                if changes:
                    history = replace(history, changed_files=tuple(sorted(set(history.changed_files) | set(changes))))
                    failures.append(CycleFailure('scope_violation', 'Re-Test modified artifacts: ' + ', '.join(changes)))
            except Exception as error:
                failures.append(CycleFailure('artifact_observation', str(error)))
        try:
            save_bundle()
            history = replace(history, prompt_artifact_path=bundle_path)
            if any(f.kind in ('scope_violation', 'artifact_observation', 'artifact_change_not_established') for f in failures):
                if load_current_state(request.state_file)['status'] != 'implementation_failed':
                    self._transition(request, 'implementation_failed', 'Correction could not safely complete')
                return finish()
            record_errors = tuple(f.detail for f in failures)
            execution_results = [attempt.execution_result for attempt in history.attempts] + [history.retest_result]
            record_errors += tuple(result.errors for result in execution_results if result and result.errors.strip() != 'NONE')
            record_warnings = tuple(result.warnings for result in execution_results if result and result.warnings.strip() != 'NONE')
            if any(event.test_phase and (event.status != 'completed' or event.exit_code is None) for event in events):
                record_errors += ('Test command execution error observed in command trace',)
            record_path = self._recorder.record(
                implementation_id=identity, recorded_at=datetime.now().astimezone(), command_events=tuple(events),
                test_required=request.tests.behavior_change,
                tests_created_or_modified=tuple(name for name in history.changed_files
                    if name in {str(path).replace('\\', '/') for path in test_paths}),
                errors=record_errors, warnings=record_warnings,
                no_tdd_reason=None if request.tests.behavior_change else 'Caller explicitly declared non-behavior-changing Correction',
            )
            test_provider = self._test_provider(record_path, identity)
            test_state = test_provider.get_state()
            record_data = json.loads(record_path.read_text(encoding='utf-8'))
            history = replace(history, test_execution_record_path=record_path,
                              command_trace_path=Path(record_data['command_trace_path']), test_state=test_state)
            for command, phase in request.tests.commands():
                if not any(event.test_phase == phase and event.command in (command, f'specflow-test --phase {phase} -- {command}')
                           for event in events):
                    failures.append(CycleFailure('evidence_generation', 'Required Test execution evidence unavailable'))
                    return finish()
        except Exception as error:
            failures.append(CycleFailure('evidence_generation', f'{type(error).__name__}: {error}'))
            return finish()
        basis = old.basis
        evidence = CollectImplementationEvidenceUseCase(self._repository, test_provider, self._evidence_repository).execute(
            CollectImplementationEvidenceInput(
                base_branch=old.identity.base_branch, test_execution_record_path=record_path,
                implementation_id=identity, implementation_kind='CORRECTION', previous_evidence_id=old.identity.evidence_id,
                specification_path=basis.specification_path, specification_approval_id=basis.specification_approval_id,
                implementation_plan_path=basis.implementation_plan_path, implementation_plan_approval_id=basis.implementation_plan_approval_id,
                codex_prompt_path=bundle_path, codex_prompt=bundle_path.read_text(encoding='utf-8'),
                implementation_branch=old.identity.implementation_branch, base_commit=old.identity.base_commit,
                implementation_result=replace(parsed, changed_files='\n'.join(history.changed_files),
                    executed_commands='\n'.join(event.command for event in events)) if parsed else None, approved_scope=old.scope,
            ))
        if not evidence.success or evidence.implementation_evidence is None or evidence.evidence_path is None:
            failures.append(CycleFailure('evidence_generation', evidence.error_message or 'New Evidence unavailable'))
            return finish()
        history = replace(history, new_evidence_id=evidence.evidence_id)
        prepare = PrepareReviewInputUseCase(evidence_repository=self._evidence_repository,
            approval_repository=self._approvals, repository_state_provider=self._repository,
            test_state_provider_factory=self._test_provider)
        prepared = prepare.execute(replace(previous.request, implementation_id=identity, evidence_id=evidence.evidence_id,
            source_paths=source_paths, test_paths=test_paths,
            collection_missing_evidence=evidence.missing_evidence, collection_inconsistencies=evidence.inconsistencies,
            collection_human_approval_required=evidence.human_approval_required))
        history = replace(history, failures=tuple(failures))
        prepared = replace(prepared, history_context=history_context(history, request.tests))
        if prepared.review_input is None:
            failures.append(CycleFailure('re_review', 'Required new Review Input unavailable'))
            self._transition(request, 'review_failed', 'Required Re-Review Input unavailable')
            return finish()
        self._transition(request, 'reviewing', 'New Correction Evidence saved; Re-Review started')
        reviewer = ReviewWithRetryUseCase(self._ai, self._retry_authorize)
        reviewed = reviewer.classify(reviewer.execute(prepared, mode=routing.request.review.review.mode))
        final_state = 'reviewing'
        if reviewed.classification.result is None:
            final_state = 'review_failed'
            failures.append(CycleFailure('re_review', 'Re-Review did not establish a Result'))
            self._transition(request, final_state, 'Re-Review did not establish a Result')
        return finish()
