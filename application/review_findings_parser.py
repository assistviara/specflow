import json
from application.review_findings import ASPECTS, AspectReview, ReviewFinding


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f'Expected exactly these keys: {expected}')


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty text')
    return value


def _texts(value):
    if not isinstance(value, list):
        raise ValueError('Expected text array')
    return tuple(_text(item) for item in value)


def _reference(reference, context):
    value = context
    for part in reference.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise ValueError(f'Unknown input reference: {reference}')
    if value is None:
        raise ValueError(f'Unavailable input reference: {reference}')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate response key: {key}')
        result[key] = value
    return result


def parse_review_findings(content: str, context: dict) -> tuple[AspectReview, ...]:
    data = json.loads(content, object_pairs_hook=_unique_object)
    _keys(data, ('aspects',))
    if not isinstance(data['aspects'], list) or len(data['aspects']) != len(ASPECTS):
        raise ValueError('All five aspects are required')
    reviews = {}
    for item in data['aspects']:
        _keys(item, ('aspect', 'checked', 'findings', 'unconfirmed'))
        aspect = _text(item['aspect'])
        if aspect not in ASPECTS or aspect in reviews:
            raise ValueError('Unknown or duplicate aspect')
        checked = _text(item['checked'])
        unconfirmed = _texts(item['unconfirmed'])
        if not isinstance(item['findings'], list):
            raise ValueError('Expected findings array')
        findings = []
        for finding in item['findings']:
            _keys(finding, ('description', 'rationale', 'references'))
            description = _text(finding['description'])
            rationale = _text(finding['rationale'])
            references = _texts(finding['references'])
            if not references:
                raise ValueError('Finding requires input references')
            for reference in references:
                _reference(reference, context)
            findings.append(ReviewFinding(aspect, description, rationale, references, 'semantic'))
        reviews[aspect] = AspectReview(aspect, checked, tuple(findings), unconfirmed)
    return tuple(reviews[aspect] for aspect in ASPECTS)
