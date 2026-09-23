from application.correction_validation import validate_routing
from application.correction_cycle import CycleFailure
from core.approval_validation import validate_approval_result


def validate_cycle(request, state, evidence_repository, approval_repository):
    errors = list(validate_routing(request.routing.request))
    if not request.routing.ready:
        errors.append('Correction Routing is not ready')
    if state != 'correction_requested':
        errors.append('Correction requires correction_requested State')
    inp = request.routing.request.review.review.prepared.review_input
    if inp is None or inp.evidence is None:
        return (CycleFailure('start_condition', 'Previous Evidence is unavailable'),)
    old = inp.evidence
    try:
        if evidence_repository.load(old.identity.evidence_id) != old:
            errors.append('Previous Evidence does not correspond to the reviewed snapshot')
    except Exception as error:
        errors.append(f'Previous Evidence unavailable: {error}')
    for approval_id, path, kind in (
        (old.basis.specification_approval_id, old.basis.specification_path, 'specification'),
        (old.basis.implementation_plan_approval_id, old.basis.implementation_plan_path, 'implementation_plan'),
    ):
        validation = validate_approval_result(approval_repository.get(approval_id), str(path), kind)
        errors.extend(validation.validation_errors)
    for instruction in request.routing.instructions:
        if instruction.destination != 'Codex再実装工程':
            errors.append(f'Automatic execution unsupported: {instruction.destination}')
        if (instruction.allowed_changes != old.scope.allowed_changes
                or instruction.forbidden_changes != old.scope.forbidden_changes):
            errors.append('Instruction changed the approved Scope')
    plan = request.tests
    groups = (plan.target_commands, plan.required_commands, plan.existing_commands)
    if plan.behavior_change:
        groups = (*groups, plan.full_commands)
    if any(not group or any(not isinstance(command, str) or not command.strip() for command in group) for group in groups):
        errors.append('Required Re-Test commands are not established')
    return tuple(CycleFailure('start_condition', error) for error in errors)
