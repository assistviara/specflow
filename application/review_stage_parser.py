import json
from application.review_findings import ASPECTS, ReviewFinding
from application.review_findings_parser import _keys, _text, _texts, _reference, _unique_object
from application.review_stages import StageAssessment


def parse_stage_response(content: str, context: dict) -> StageAssessment:
    data = json.loads(content, object_pairs_hook=_unique_object)
    _keys(data, ('stage', 'checked', 'findings', 'unconfirmed'))
    if data['stage'] != context['stage']:
        raise ValueError('Response stage does not match requested stage')
    checked = _text(data['checked'])
    unconfirmed = _texts(data['unconfirmed'])
    if not isinstance(data['findings'], list):
        raise ValueError('Expected findings array')
    findings = []
    for item in data['findings']:
        _keys(item, ('aspect', 'description', 'rationale', 'references'))
        aspect = _text(item['aspect'])
        if aspect not in ASPECTS:
            raise ValueError('Unknown review aspect')
        references = _texts(item['references'])
        if not references:
            raise ValueError('Finding requires references')
        for reference in references:
            _reference(reference, context)
        findings.append(ReviewFinding(aspect, _text(item['description']), _text(item['rationale']), references, 'semantic'))
    return StageAssessment(checked, tuple(findings), unconfirmed)
