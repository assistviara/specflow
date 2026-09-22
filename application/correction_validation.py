from application.classify_review_result import _review_failures
from application.correction_routing import ReturnDestination
from application.review_result import ReviewResult
from application.review_result_parser import validate_result_report
from application.review_result_prompt import result_context
from application.review_findings_parser import _reference


BASE = 'review.prepared.review_input'


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _require_reference(reference, context, roots):
    if not _text(reference) or not any(reference == root or reference.startswith(root + '.') for root in roots):
        raise ValueError('Reference must identify the required approved content')
    _reference(reference, context)
    value = context
    for part in reference.split('.'):
        value = value[int(part)] if isinstance(value, list) else value[part]
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValueError('Required reference content is empty')


def validate_routing(request) -> tuple[str, ...]:
    output = request.review
    errors = []
    if output.result != ReviewResult.REVISION_REQUIRED:
        errors.append('Established REVISION_REQUIRED is required')
    if output.review_failures or output.execution_error or output.parse_error or output.validation_errors:
        errors.append('Unresolved Review failure or invalid Review Report')
    errors.extend(_review_failures(output.review))
    if any(history.recovery_failed for history in request.retry_history):
        errors.append('Recovery Failed')
    if request.current_state not in ('reviewing', 'correction_requested'):
        errors.append('Current reviewing/correction_requested State is not confirmed')
    control = request.control
    if control is None:
        errors.append('Routing control unavailable')
    else:
        if control.correction_allowed is not True:
            errors.append('Correction is not explicitly allowed')
        if control.early_stop_triggered is not False:
            errors.append('Early Stop is triggered or unconfirmed')
        if type(control.correction_count) is not int or control.correction_count < 0:
            errors.append('Correction Count unavailable or invalid')
        if control.count_condition_met is not True:
            errors.append('Caller has not confirmed Count condition')
    report = output.report
    inp = output.review.prepared.review_input
    if report is None or inp is None or inp.evidence is None:
        return tuple((*errors, 'Review Report or approved input unavailable'))
    if report.proposed_result != ReviewResult.REVISION_REQUIRED:
        errors.append('Review Report does not establish REVISION_REQUIRED')
    context = result_context(output.review)
    errors.extend(validate_result_report(report, context))
    if not _text(report.rationale) or not report.references:
        errors.append('Review rationale and references are required')
    for ref in report.references:
        try:
            _reference(ref, context)
        except ValueError as error:
            errors.append(str(error))
    # Use Target 1's acquired approval records; do not reacquire/rebuild its comparisons.
    approved = {record.get('approval_id') for record in inp.approval_records if record.get('decision') == 'approved'}
    basis = inp.evidence.basis
    if not {basis.specification_approval_id, basis.implementation_plan_approval_id} <= approved:
        errors.append('Existing Specification/Plan approvals unavailable')
    if not request.problems:
        errors.append('Explicit correction problems are required')
    auto_destinations = {ReturnDestination.PROMPT, ReturnDestination.IMPLEMENTATION, ReturnDestination.TEST}
    targets = []
    for index, problem in enumerate(request.problems):
        prefix = f'Problem {index}: '
        try:
            destination = ReturnDestination(problem.destination)
        except (ValueError, TypeError):
            errors.append(prefix + 'Return Destination is not explicitly established')
        else:
            if destination not in auto_destinations:
                errors.append(prefix + f'{destination.value} requires Human/approval process; no automatic Instruction')
        if problem.safe_in_scope is not True or not _text(problem.safe_scope_reason):
            errors.append(prefix + 'Safe in-scope correction is not confirmed')
        if problem.scope_reference != f'{BASE}.evidence.scope':
            errors.append(prefix + 'Approved Scope reference is not established')
        if not problem.targets or any(not _text(target) or target not in report.targets for target in problem.targets):
            errors.append(prefix + 'Targets are missing or do not correspond to Review Report')
        targets.extend(problem.targets)
        if not problem.finding_references:
            errors.append(prefix + 'Original Finding references are required')
        for ref in problem.finding_references:
            if ref not in context['concerns'] or '.findings.' not in ref:
                errors.append(prefix + f'Unknown original Finding: {ref}')
        approved_roots = (f'{BASE}.specification.content', f'{BASE}.implementation_plan.content',
                          f'{BASE}.evidence.scope.allowed_changes')
        for name, references, roots in (
            ('Required Tests', problem.required_test_references, (*approved_roots,
                f'{BASE}.codex_prompt.content', f'{BASE}.tests', f'{BASE}.evidence.verification.test_commands')),
            ('Approved corrective requirements', problem.correction_references, approved_roots),
        ):
            if not references:
                errors.append(prefix + name + ' references are required')
            for ref in references:
                try:
                    _require_reference(ref, context, roots)
                except ValueError as error:
                    errors.append(prefix + str(error))
        if problem.safe_group is not None and not _text(problem.safe_group):
            errors.append(prefix + 'Safe grouping confirmation must be nonempty')
    if set(targets) != set(report.targets):
        errors.append('Some Review correction targets are not routed; partial routing is forbidden')
    finding_refs = {ref for ref in context['concerns'] if '.findings.' in ref}
    covered = {ref for problem in request.problems for ref in problem.finding_references}
    if not finding_refs <= covered:
        errors.append('Some original Findings have no explicit routing; partial routing is forbidden')
    return tuple(errors)
