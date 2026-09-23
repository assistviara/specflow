import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from application.codex_execution import CodexCommandEvent, CodexJsonlParseResult
from application.prepare_correction import PrepareCorrectionUseCase
from core.ai.ai_response import AIResponse
from core.ai.ai_service import AIService
from test_correction_routing import routing_case
from test_classify_review_result import result_case, evaluation
from test_prepare_review_input import review_case


def report(status='NOT_RUN', result='NONE'):
    return f'''## Implementation Summary
TEST_REQUIRED: YES
Corrected approved validation.
## Changed Files
source.py
## Executed Commands
target-test
full-test
## Test Execution Status
{status}
## Test Result
{result}
## Test Execution Error
TECHNICAL_RETRY_SAFE: NO
TECHNICAL_RETRY_OPERATION: NONE
## Errors
NONE
## Warnings
NONE
## Incomplete Items
NONE
## Human Approval Required
NONE
'''


@pytest.fixture
def cycle_case(routing_case):
    from application.correction_cycle import CorrectionCycleInput, ReTestPlan
    from application.execute_correction_cycle import ExecuteCorrectionCycleUseCase
    from infrastructure.json_implementation_evidence_repository import JsonImplementationEvidenceRepository
    from infrastructure.json_test_execution_recorder import JsonTestExecutionRecorder
    from infrastructure.json_test_execution_record_repository import JsonTestExecutionRecordRepository
    from infrastructure.json_command_trace_repository import JsonCommandTraceRepository
    from infrastructure.json_test_state_provider import JsonTestStateProvider
    from application.review_retry import RetryAuthorization

    c, routing_request, routing_runner = routing_case
    routing = PrepareCorrectionUseCase(AIService(routing_runner)).execute(routing_request)
    root = c['request'].repository_path
    directory = root / 'evidence'
    repo = JsonImplementationEvidenceRepository(directory)
    old = routing.request.review.review.prepared.review_input.evidence
    old_path = repo.save(old)
    state_file = root / 'state.json'
    state_file.write_text(json.dumps({'status': 'correction_requested'}))
    request = CorrectionCycleInput(routing, state_file, root / 'state_history', directory,
                                   ReTestPlan(('target-test',), ('required-test',), ('existing-test',), ('full-test',), True))
    calls = []
    adapter = Mock()
    def run(*, prompt, working_directory):
        if '"operation": "RE_TEST_ONLY"' in prompt:
            calls.append('retest')
            events = tuple(CodexCommandEvent(i + 1, str(i), cmd, 'completed', 0, 'passed', phase)
                           for i, (cmd, phase) in enumerate((('target-test', 'target'), ('required-test', 'target'),
                                                           ('existing-test', 'target'), ('full-test', 'full'))))
            return CodexJsonlParseResult('', events, report('COMPLETED', 'PASS'), True, ())
        calls.append('correction')
        (root / 'source.py').write_text('value = 2\n')
        initial = CodexCommandEvent(1, 'initial', 'initial-test', 'completed', 1, 'expected failure', 'initial')
        return CodexJsonlParseResult('', (initial,), report(), True, ())
    adapter.run.side_effect = run
    runner = Mock()
    def review(ai_request):
        calls.append('review')
        if ai_request.prompt.startswith('# Review Result Evaluation'):
            return AIResponse(json.dumps(evaluation('HUMAN_REVIEW_REQUIRED') | {'human_questions': ['Confirm observed behavior'],
                'references': ['review.prepared.review_input.implementation_plan.content']}), True)
        return AIResponse(json.dumps({'aspects': [dict(aspect=a, checked='Compared correction history', findings=[], unconfirmed=[])
                                                for a in ('Requirement', 'Scope', 'Implementation', 'Test', 'Evidence')]}), True)
    runner.run.side_effect = review
    def snapshot(root_path):
        return {str(p.relative_to(root_path)).replace('\\', '/'): p.read_bytes()
                for p in root_path.rglob('*') if p.is_file() and directory not in p.parents
                and request.state_history_dir not in p.parents and p != state_file}
    recorder = JsonTestExecutionRecorder(trace_repository=JsonCommandTraceRepository(directory),
                                        record_repository=JsonTestExecutionRecordRepository(directory))
    provider_factory = lambda path, identity: JsonTestStateProvider(record_path=path, expected_implementation_id=identity)
    authorize = Mock(return_value=RetryAuthorization())
    use_case = ExecuteCorrectionCycleUseCase(adapter=adapter, recorder=recorder, evidence_repository=repo,
        repository_state_provider=c['repository_state'], approval_repository=c['approvals'],
        test_state_provider_factory=provider_factory, ai_service=AIService(runner), snapshot=snapshot, retry_authorize=authorize)
    return dict(c=c, request=request, use_case=use_case, adapter=adapter, runner=runner, calls=calls,
                repo=repo, old=old, old_path=old_path, recorder=recorder, authorize=authorize)


def test_corrects_retests_and_rereviews_with_new_evidence_preserving_previous_history(cycle_case):
    c = cycle_case
    old_bytes = c['old_path'].read_bytes()
    output = c['use_case'].execute(c['request'])
    assert c['calls'][:2] == ['correction', 'retest']
    assert output.history.correction_count == 1
    assert output.history.changed_files == ('source.py',)
    assert output.history.implementation_id != c['old'].identity.implementation_id
    assert output.evidence.success
    new = output.evidence.implementation_evidence
    assert new.identity.evidence_id != c['old'].identity.evidence_id
    assert new.identity.previous_evidence_id == c['old'].identity.evidence_id
    assert new.identity.implementation_kind == 'CORRECTION'
    assert new.identity.base_commit == c['old'].identity.base_commit
    assert new.identity.base_branch == c['old'].identity.base_branch
    assert new.identity.implementation_branch == c['old'].identity.implementation_branch
    assert c['old_path'].read_bytes() == old_bytes
    record = json.loads(new.verification.test_execution_record_path.read_text())
    assert record['implementation_id'] == str(new.identity.implementation_id)
    assert output.history.command_trace_path.exists()
    prompts = json.loads(new.basis.codex_prompt_path.read_text(encoding='utf-8'))
    assert prompts['requests'][0]['prompt'] == c['adapter'].run.call_args_list[0].kwargs['prompt']
    assert output.prepared.review_input is not None, (output.prepared.missing_information, output.prepared.acquisition_errors)
    assert output.prepared.history_context['previous_evidence_id'] == str(c['old'].identity.evidence_id)
    assert output.prepared.history_context['new_evidence_id'] == str(new.identity.evidence_id)
    assert output.re_review.review.mode == 'BATCH'
    assert output.re_review.classification is not None
    assert output.history.routing is c['request'].routing
    assert len(c['calls']) == 4
    assert output.current_state == 'reviewing'
    assert output.history_path.exists()


def test_default_artifact_observation_uses_only_read_only_git_listing_and_detects_dirty_changes(tmp_path, monkeypatch):
    from application.correction_cycle_artifacts import snapshot_artifacts
    import subprocess
    source = tmp_path / 'source.py'
    source.write_text('already dirty')
    observed = Mock(return_value=type('GitOutput', (), {'stdout': b'source.py\0new.py\0'})())
    monkeypatch.setattr(subprocess, 'run', observed)
    before = snapshot_artifacts(tmp_path)
    source.write_text('corrected dirty file')
    (tmp_path / 'new.py').write_text('new artifact')
    after = snapshot_artifacts(tmp_path)
    assert before['source.py'] != after['source.py'] and 'new.py' not in before and 'new.py' in after
    assert observed.call_args.args[0] == ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard']


def test_existing_review_retry_can_be_authorized_without_retrying_correction_or_tests(cycle_case):
    from application.review_retry import RetryAuthorization
    c = cycle_case
    original = c['runner'].run.side_effect
    failed = False
    def run(request):
        nonlocal failed
        if not failed:
            failed = True
            return AIResponse('', False, 'temporary AI outage')
        return original(request)
    c['runner'].run.side_effect = run
    c['authorize'].return_value = RetryAuthorization(True, True, True, True, False, 'Confirmed safe temporary AI failure')
    output = c['use_case'].execute(c['request'])
    assert output.re_review.classification.result is not None
    assert output.re_review.history[0].retry_count == 1
    assert output.history.correction_count == 1
    assert c['calls'].count('correction') == 1 and c['calls'].count('retest') == 1
    assert output.history.routing is c['request'].routing
    assert len(c['calls']) == 4
    assert output.current_state == 'reviewing'
    assert output.history_path.exists()


@pytest.mark.parametrize('invalid', ['destination', 'routing', 'state', 'approval', 'old_evidence', 'target_tests',
                                    'required_tests', 'existing_tests', 'full_tests', 'scope'])
def test_does_not_start_unapproved_or_unsupported_cycle(cycle_case, invalid):
    c = cycle_case
    request = c['request']
    if invalid == 'destination':
        instruction = replace(request.routing.instructions[0], destination='Test修正工程')
        request = replace(request, routing=replace(request.routing, instructions=(instruction,)))
    elif invalid == 'routing':
        request = replace(request, routing=replace(request.routing, blocked_reasons=('Cannot route',)))
    elif invalid == 'state':
        request.state_file.write_text('{"status":"reviewing"}')
    elif invalid == 'approval':
        (c['c']['request'].repository_path / 'plan.md').write_text('changed after approval')
    elif invalid == 'old_evidence':
        c['old_path'].unlink()
    elif invalid == 'scope':
        instruction = replace(request.routing.instructions[0], allowed_changes=('*',))
        request = replace(request, routing=replace(request.routing, instructions=(instruction,)))
    else:
        field = {'target_tests': 'target_commands', 'required_tests': 'required_commands',
                 'existing_tests': 'existing_commands', 'full_tests': 'full_commands'}[invalid]
        request = replace(request, tests=replace(request.tests, **{field: ()}))
    output = c['use_case'].execute(request)
    assert output.failures
    assert output.re_review is None
    c['adapter'].run.assert_not_called()
    c['runner'].run.assert_not_called()
    assert output.history is None or output.history.correction_count == 0


def test_multiple_instructions_are_one_cycle_and_one_retest(cycle_case):
    c = cycle_case
    request = replace(c['request'], routing=replace(c['request'].routing,
                      instructions=c['request'].routing.instructions * 2))
    original = c['adapter'].run.side_effect
    n = 0
    def execute(**kwargs):
        nonlocal n
        result = original(**kwargs)
        if '"operation": "CORRECTION"' in kwargs['prompt']:
            n += 1
            (kwargs['working_directory'] / 'source.py').write_text(f'value = {2 + n}\n')
        return result
    c['adapter'].run.side_effect = execute
    output = c['use_case'].execute(request)
    assert c['calls'] == ['correction', 'correction', 'retest', 'review', 'review']
    assert len(output.history.attempts) == 2
    assert output.history.correction_count == 1
    assert output.evidence.success


@pytest.mark.parametrize('kind', ['exception_changed', 'exception_unchanged', 'process_failure', 'parse_failure',
                                  'scope_violation', 'no_change', 'reverted_change'])
def test_partial_failure_stops_remaining_work_and_counts_only_observed_change(cycle_case, kind):
    c = cycle_case
    request = replace(c['request'], routing=replace(c['request'].routing,
                      instructions=c['request'].routing.instructions * 2))
    root = c['c']['request'].repository_path
    def execute(**kwargs):
        c['calls'].append('correction')
        if kind != 'exception_unchanged' and kind != 'no_change':
            (root / 'source.py').write_text('partial change\n')
        if kind == 'scope_violation':
            (root / 'unapproved.txt').write_text('scope violation')
        if kind.startswith('exception'):
            raise RuntimeError('Codex failure')
        if kind == 'reverted_change' and len(c['calls']) == 2:
            (root / 'source.py').write_text('value = 1\n')
            raise RuntimeError('Failure after restoring earlier bytes')
        return CodexJsonlParseResult('', (), 'bad report' if kind == 'parse_failure' else report(),
                                    kind != 'process_failure', ('process stopped',) if kind == 'process_failure' else ())
    c['adapter'].run.side_effect = execute
    output = c['use_case'].execute(request)
    expected_count = 0 if kind in ('exception_unchanged', 'no_change') else 1
    assert output.history.correction_count == expected_count
    assert output.failures
    assert output.history_path.exists()
    assert output.re_review is None
    assert output.current_state == 'implementation_failed'
    assert c['calls'] == ['correction'] * (2 if kind in ('no_change', 'reverted_change') else 1)
    if kind == 'exception_changed':
        assert (root / 'source.py').read_text() == 'partial change\n'
    assert c['old_path'].exists()


@pytest.mark.parametrize('result', ['PASS', 'FAIL', 'ERROR'])
def test_retest_result_is_recorded_before_evidence_and_never_triggers_test_retry(cycle_case, result):
    c = cycle_case
    original = c['adapter'].run.side_effect
    def run(**kwargs):
        raw = original(**kwargs)
        if '"operation": "RE_TEST_ONLY"' in kwargs['prompt']:
            events = tuple(replace(event, status='failed' if result == 'ERROR' else 'completed',
                                   exit_code=None if result == 'ERROR' else int(result == 'FAIL'),
                                   output=result) for event in raw.command_events)
            return replace(raw, command_events=events, final_message=report('ERROR' if result == 'ERROR' else 'COMPLETED',
                                                                          'NONE' if result == 'ERROR' else result))
        return raw
    c['adapter'].run.side_effect = run
    output = c['use_case'].execute(c['request'])
    assert output.evidence.success
    assert output.re_review.classification is not None
    assert output.history.correction_count == 1
    test = output.history.test_state
    assert test.target_test_status == ('ERROR' if result == 'ERROR' else 'COMPLETED')
    assert test.target_test_result == ('NONE' if result == 'ERROR' else result)
    if result == 'ERROR':
        assert test.errors
    assert c['calls'].count('retest') == 1
    assert c['calls'].count('correction') == 1
    assert 'target-test' in test.test_commands and 'required-test' in test.test_commands
    assert 'existing-test' in test.test_commands and 'full-test' in test.test_commands


@pytest.mark.parametrize('failure', ['runner_exception', 'missing_commands', 'record_save', 'evidence_save', 'test_modifies_source'])
def test_cannot_rereview_without_required_evidence_or_after_test_modification(cycle_case, failure, monkeypatch):
    c = cycle_case
    original = c['adapter'].run.side_effect
    def run(**kwargs):
        if '"operation": "RE_TEST_ONLY"' in kwargs['prompt'] and failure == 'runner_exception':
            c['calls'].append('retest')
            raise RuntimeError('Test Runner unavailable')
        raw = original(**kwargs)
        if '"operation": "RE_TEST_ONLY"' in kwargs['prompt']:
            if failure == 'missing_commands':
                return replace(raw, command_events=())
            if failure == 'test_modifies_source':
                (kwargs['working_directory'] / 'source.py').write_text('modified during tests')
        return raw
    c['adapter'].run.side_effect = run
    if failure == 'record_save':
        monkeypatch.setattr(c['recorder'], 'record', Mock(side_effect=OSError('record unavailable')))
    if failure == 'evidence_save':
        monkeypatch.setattr(c['repo'], 'save', Mock(side_effect=OSError('evidence unavailable')))
    output = c['use_case'].execute(c['request'])
    assert output.failures
    assert output.re_review is None
    assert output.history.correction_count == 1
    assert output.history_path.exists()
    c['runner'].run.assert_not_called()
    assert c['old_path'].exists()


def test_partial_codex_failure_can_rereview_when_recordable_evidence_exists(cycle_case):
    c = cycle_case
    request = replace(c['request'], routing=replace(c['request'].routing,
                      instructions=c['request'].routing.instructions * 2))
    original = c['adapter'].run.side_effect
    def run(**kwargs):
        raw = original(**kwargs)
        events = list(raw.command_events)
        events.extend(CodexCommandEvent(i + 2, str(i), command, 'completed', 1, 'FAIL', phase)
                      for i, (command, phase) in enumerate(request.tests.commands()))
        return replace(raw, command_events=tuple(events), process_succeeded=False, errors=('Codex disconnected after testing',))
    c['adapter'].run.side_effect = run
    output = c['use_case'].execute(request)
    assert output.history.correction_count == 1
    assert len(output.history.attempts) == 1
    assert output.history.failures[0].kind == 'codex_execution'
    assert output.evidence.success
    assert output.re_review.classification is not None
    assert c['calls'].count('correction') == 1
    assert 'retest' not in c['calls']


@pytest.mark.parametrize('failure', ['execution', 'parse', 'input'])
def test_rereview_failure_preserves_history_and_does_not_invent_result(cycle_case, failure, monkeypatch):
    c = cycle_case
    if failure == 'input':
        from application.prepare_review_input import PrepareReviewInputUseCase
        original = PrepareReviewInputUseCase.execute
        def unavailable(self, request):
            output = original(self, request)
            return replace(output, review_input=None, missing_information=('Required current Source',))
        monkeypatch.setattr(PrepareReviewInputUseCase, 'execute', unavailable)
    else:
        c['runner'].run.side_effect = lambda request: AIResponse('invalid json', failure != 'execution',
                                                                'AI unavailable' if failure == 'execution' else None)
    output = c['use_case'].execute(c['request'])
    assert output.current_state == 'review_failed'
    assert output.re_review is None or output.re_review.classification.result is None
    assert output.failures
    assert output.history.new_evidence_id is not None
    assert output.history.routing is c['request'].routing
    assert output.history.correction_count == 1
    if failure == 'input':
        c['runner'].run.assert_not_called()


@pytest.mark.parametrize('mode', ['BATCH', 'STAGED'])
@pytest.mark.parametrize('result', ['APPROVED', 'REVISION_REQUIRED', 'HUMAN_REVIEW_REQUIRED', None])
def test_history_is_visible_to_real_review_parsers_and_every_result_ends_the_cycle(cycle_case, mode, result):
    from test_classify_review_result import staged, resolution
    from application.review_result_parser import APPROVAL_CHECKS
    c = cycle_case
    request = c['request']
    if mode == 'STAGED':
        previous = staged(request.routing.request.review.review)
        report = replace(request.routing.request.review.report, references=(
            'review.stages.0.assessment.findings.0', 'review.prepared.review_input.implementation_plan.content'))
        previous_result = replace(request.routing.request.review, review=previous, report=report)
        problem = replace(request.routing.request.problems[0], finding_references=('review.stages.0.assessment.findings.0',))
        routing_request = replace(request.routing.request, review=previous_result, problems=(problem,))
        instruction = replace(request.routing.instructions[0], finding_references=problem.finding_references)
        request = replace(request, routing=replace(request.routing, request=routing_request, instructions=(instruction,)))
    previous_findings = request.routing.request.review.review
    captured = []
    def respond(ai_request):
        c['calls'].append('review')
        if ai_request.prompt.startswith('# Review Result Evaluation'):
            context = json.loads(ai_request.prompt.split('# Result Input\n')[1])
            if result is None:
                return AIResponse('invalid result', True)
            data = evaluation(result)
            data['references'] = ['review.prepared.history_context.previous_evidence_id']
            if result == 'APPROVED':
                data.update(problem='', cause='', targets=[], safe_scope_reason='', human_questions=[], unresolved=[])
                data['checks'] = {key: dict(confirmed=True, rationale='Verified current implementation',
                    references=['review.prepared.review_input.implementation_plan.content']) for key in APPROVAL_CHECKS}
                data['resolutions'] = [resolution(ref) for ref in context['concerns']]
            elif result == 'HUMAN_REVIEW_REQUIRED':
                data['human_questions'] = ['Confirm requirement interpretation']
            return AIResponse(json.dumps(data), True)
        header = '# Review Input\n' if mode == 'BATCH' else '# Stage Input\n'
        context = json.loads(ai_request.prompt.split(header)[1])
        history = context['history_context']
        captured.append(history)
        assert history['previous_review']['result'] == 'REVISION_REQUIRED'
        assert history['previous_evidence_id'] != history['new_evidence_id']
        assert history['instructions'] and history['correction_history']['attempts']
        finding = dict(description='Current issue evaluated against previous correction', rationale='Compared old and new states',
                       references=['history_context.previous_review.report.problem'])
        if mode == 'BATCH':
            return AIResponse(json.dumps({'aspects': [dict(aspect=a, checked='History comparison', findings=[finding] if i == 0 else [], unconfirmed=[])
                for i, a in enumerate(('Requirement', 'Scope', 'Implementation', 'Test', 'Evidence'))]}), True)
        return AIResponse(json.dumps(dict(stage=context['stage'], checked='History comparison',
                                         findings=[dict(aspect='Requirement', **finding)], unconfirmed=[])), True)
    c['runner'].run.side_effect = respond
    output = c['use_case'].execute(request)
    assert output.re_review.review.mode == mode
    actual = output.re_review.classification.result
    assert (actual.value if actual else None) == result
    assert len(captured) == (1 if mode == 'BATCH' else 5)
    assert output.history.routing.request.review.review is previous_findings
    assert c['calls'].count('correction') == 1 and c['calls'].count('retest') == 1
    assert output.current_state == ('review_failed' if result is None else 'reviewing')
    assert output.history.correction_count == 1
    transitions = [json.loads(p.read_text(encoding='utf-8'))['to_state'] for p in request.state_history_dir.glob('*.json')]
    assert 'implementing' in transitions and 'implementation_completed' in transitions and 'reviewing' in transitions
    assert not set(transitions) & {'completed', 'correcting', 'final_approval_pending'}


@pytest.mark.parametrize('destination', ['Specification策定工程', 'Plan修正工程', 'Prompt再生成工程',
                                        'Test修正工程', 'Human判断', 'Critical Change Approval工程'])
def test_every_other_destination_stops_before_any_instruction(cycle_case, destination):
    c = cycle_case
    original = c['request'].routing.instructions[0]
    request = replace(c['request'], routing=replace(c['request'].routing,
                      instructions=(original, replace(original, destination=destination))))
    output = c['use_case'].execute(request)
    assert output.failures and output.request.routing.instructions[1].destination == destination
    c['adapter'].run.assert_not_called()


def test_saved_identity_is_preserved_when_observed_repository_state_differs(cycle_case):
    c = cycle_case
    observed = c['c']['repository_state'].get_state.return_value
    original = c['adapter'].run.side_effect
    def run(**kwargs):
        raw = original(**kwargs)
        c['c']['repository_state'].get_state.return_value = replace(observed, branch='observed-branch')
        return raw
    c['adapter'].run.side_effect = run
    output = c['use_case'].execute(c['request'])
    assert output.evidence.implementation_evidence.identity.implementation_branch == c['old'].identity.implementation_branch
    assert output.prepared.review_input.repository_state.branch == 'observed-branch'
    assert output.prepared.mismatches


def test_cycle_has_no_git_mutation_approval_or_next_cycle_side_effects(cycle_case, monkeypatch):
    import subprocess
    from application.technical_review_retry import TechnicalReviewRetryUseCase
    c = cycle_case
    forbidden = Mock(side_effect=AssertionError('Unexpected process execution'))
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    output = c['use_case'].execute(c['request'])
    assert output.re_review
    forbidden.assert_not_called()
    c['c']['approvals'].save.assert_not_called()
    assert len(output.history.attempts) == 1


def test_scope_check_rejects_path_outside_approved_targets_even_with_broad_extension_allowance(cycle_case):
    c = cycle_case
    original = c['adapter'].run.side_effect
    def run(**kwargs):
        raw = original(**kwargs)
        (kwargs['working_directory'] / 'unapproved.py').write_text('outside target paths')
        return raw
    c['adapter'].run.side_effect = run
    output = c['use_case'].execute(c['request'])
    assert any(f.kind == 'scope_violation' for f in output.failures)
    assert output.history.correction_count == 1
    assert output.re_review is None
    assert c['calls'] == ['correction']


def test_execution_warnings_errors_and_changed_tests_remain_traceable(cycle_case):
    c = cycle_case
    original = c['adapter'].run.side_effect
    def run(**kwargs):
        raw = original(**kwargs)
        if '"operation": "CORRECTION"' in kwargs['prompt']:
            (kwargs['working_directory'] / 'test_source.py').write_text('assert value == 2\n')
        return replace(raw, final_message=raw.final_message.replace('## Warnings\nNONE', '## Warnings\nObserved warning'))
    c['adapter'].run.side_effect = run
    output = c['use_case'].execute(c['request'])
    assert output.history.attempts[0].execution_result.warnings == 'Observed warning'
    assert output.history.retest_result.warnings == 'Observed warning'
    assert 'Observed warning' in output.history.test_state.warnings
    assert 'test_source.py' in output.history.test_state.tests_created_or_modified


def test_original_codex_failure_is_not_lost_when_scope_violation_is_also_observed(cycle_case):
    c = cycle_case
    def run(**kwargs):
        (kwargs['working_directory'] / 'forbidden.txt').write_text('partial write')
        raise RuntimeError('original Codex failure')
    c['adapter'].run.side_effect = run
    output = c['use_case'].execute(c['request'])
    assert {'codex_execution', 'scope_violation'} <= {f.kind for f in output.failures}
    assert any('original Codex failure' in f.detail for f in output.history.failures)
    assert output.history.correction_count == 1


def test_prompt_save_failure_retains_partial_cycle_and_stops(cycle_case, monkeypatch):
    c = cycle_case
    original = Path.open
    def fail_prompt(path, *args, **kwargs):
        if path.name.startswith('correction_prompt_'):
            raise OSError('Cannot save actual prompt')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail_prompt)
    output = c['use_case'].execute(c['request'])
    assert output.failures and output.history.correction_count == 0
    assert output.history_path.exists()
    c['adapter'].run.assert_not_called()


def test_nonbehavior_correction_does_not_invent_missing_initial_or_full_tests(cycle_case):
    c = cycle_case
    request = replace(c['request'], tests=replace(c['request'].tests, behavior_change=False, full_commands=()))
    original = c['adapter'].run.side_effect
    def run(**kwargs):
        raw = original(**kwargs)
        return replace(raw, command_events=tuple(event for event in raw.command_events if event.test_phase not in ('initial', 'full')),
                       final_message=raw.final_message.replace('TEST_REQUIRED: YES', 'TEST_REQUIRED: NO'))
    c['adapter'].run.side_effect = run
    output = c['use_case'].execute(request)
    assert output.evidence.success
    assert output.prepared.review_input is not None
    assert output.history.test_state.initial_test_status == 'NOT_RUN'
    assert output.history.test_state.full_test_status == 'NOT_RUN'
    assert output.re_review.classification is not None


def test_explicit_current_source_and_test_selection_reaches_target_one(cycle_case):
    c = cycle_case
    root = c['c']['request'].repository_path
    (root / 'related_source.py').write_text('needed unchanged context')
    (root / 'related_test.py').write_text('needed additional test context')
    request = replace(c['request'], source_paths=(Path('source.py'), Path('related_source.py')),
                      test_paths=(Path('test_source.py'), Path('related_test.py')))
    output = c['use_case'].execute(request)
    assert output.prepared.review_input.sources[1].content == 'needed unchanged context'
    assert output.prepared.review_input.tests[1].content == 'needed additional test context'
    assert output.history.correction_count == 1
