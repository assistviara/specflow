import json
from dataclasses import fields

from application.correction_routing import CorrectionInstruction
from application.review_findings_parser import _keys, _unique_object


def parse_correction_instructions(content: str) -> list[dict]:
    data = json.loads(content, object_pairs_hook=_unique_object)
    _keys(data, ('instructions',))
    if not isinstance(data['instructions'], list):
        raise ValueError('Expected instructions array')
    if any(not isinstance(item, dict) for item in data['instructions']):
        raise ValueError('Expected instruction objects')
    return data['instructions']


def validate_correction_instructions(items: list[dict], expected: list[dict]) -> tuple[str, ...]:
    if len(items) != len(expected):
        return ('Incomplete instruction set; partial routing is forbidden',)
    errors = []
    keys = {field.name for field in fields(CorrectionInstruction)}
    for index, (item, source) in enumerate(zip(items, expected)):
        if set(item) != keys:
            errors.append(f'Instruction {index}: missing or unapproved fields')
        elif item != source:
            errors.append(f'Instruction {index}: changed grounded content, scope, destination or references')
    return tuple(errors)
