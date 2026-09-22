import json
from application.review_result import ReviewResult, ReviewResultReport
from application.review_findings_parser import _keys, _text, _texts, _reference, _unique_object

APPROVAL_CHECKS = ('specification', 'plan', 'scope', 'no_major_issues', 'tests_executed', 'test_behavior')


def _references(value, context):
    references = _texts(value)
    if not references:
        raise ValueError('Evaluation requires evidence references')
    for reference in references:
        _reference(reference, context)
    return references


def parse_result_report(content: str, context: dict) -> ReviewResultReport:
    data = json.loads(content, object_pairs_hook=_unique_object)
    _keys(data, ('result', 'rationale', 'references', 'checks', 'resolutions', 'problem', 'cause', 'targets', 'safe_scope_reason', 'human_questions', 'unresolved'))
    result = ReviewResult(_text(data['result']))
    references = _references(data['references'], context)
    if not isinstance(data['checks'], dict) or set(data['checks']) - set(APPROVAL_CHECKS):
        raise ValueError('Unknown approval condition')
    for check in data['checks'].values():
        _keys(check, ('confirmed', 'rationale', 'references'))
        if not isinstance(check['confirmed'], bool):
            raise ValueError('Approval confirmation must be boolean')
        _text(check['rationale'])
        _references(check['references'], context)
    if not isinstance(data['resolutions'], list):
        raise ValueError('Expected resolutions array')
    seen = set()
    for resolution in data['resolutions']:
        _keys(resolution, ('reference', 'disagreement', 'explanation', 'references'))
        reference = _text(resolution['reference'])
        if reference not in context['concerns'] or reference in seen:
            raise ValueError('Unknown or duplicate concern resolution')
        seen.add(reference)
        _text(resolution['disagreement'])
        _text(resolution['explanation'])
        evidence_references = _references(resolution['references'], context)
        if not any(ref != reference and ref.startswith('review.') for ref in evidence_references):
            raise ValueError('Resolution requires supporting evidence beyond the original concern')
    for field in ('problem', 'cause', 'safe_scope_reason'):
        if not isinstance(data[field], str):
            raise ValueError(f'{field} must be text')
    return ReviewResultReport(result, _text(data['rationale']), references,
                              data['checks'], tuple(data['resolutions']), data['problem'], data['cause'],
                              _texts(data['targets']), data['safe_scope_reason'], _texts(data['human_questions']), _texts(data['unresolved']))


def validate_result_report(report: ReviewResultReport, context: dict) -> tuple[str, ...]:
    errors = []
    if report.proposed_result == ReviewResult.APPROVED:
        for key in APPROVAL_CHECKS:
            if key not in report.checks or not report.checks[key]['confirmed']:
                errors.append(f'Approval condition not confirmed: {key}')
        resolved = {item['reference'] for item in report.resolutions}
        for reference in context['concerns']:
            if reference not in resolved:
                errors.append(f'Concern not resolved: {reference}')
        if report.unresolved or report.human_questions or report.targets or report.problem.strip():
            errors.append('Approval proposal retains unresolved problems or required action')
    elif report.proposed_result == ReviewResult.REVISION_REQUIRED:
        for key in ('problem', 'cause', 'safe_scope_reason'):
            if not getattr(report, key).strip():
                errors.append(f'Revision basis missing: {key}')
        if not report.targets:
            errors.append('Revision target missing')
        if report.human_questions:
            errors.append('Safe in-scope correction not established: Human decision remains')
    elif not report.human_questions:
        errors.append('Human decision question missing')
    return tuple(errors)
