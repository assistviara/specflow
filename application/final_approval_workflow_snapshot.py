"""Only Target 6's frozen Target and pre-merge DTO checkpoints.

The file cannot select Python types or import modules. Restoration follows the
existing DTO annotations from two fixed roots, including retained Review history.
"""
from dataclasses import fields, is_dataclass
from datetime import datetime, date
from enum import Enum
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from types import UnionType
from typing import get_args, get_origin, get_type_hints, Union
from uuid import UUID

from application.final_approval_target import FinalApprovalTargetOutput
from application.merge_preconditions import MergePreconditionsOutput


def _pack(value):
    if is_dataclass(value):
        return {f.name: _pack(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Enum):
        return {'enum': value.value}
    if isinstance(value, (Path, UUID, datetime, date)):
        return {'scalar': type(value).__name__ if not isinstance(value, Path) else 'Path', 'value': str(value)}
    if isinstance(value, tuple):
        return {'tuple': [_pack(v) for v in value]}
    if isinstance(value, list):
        return [_pack(v) for v in value]
    if isinstance(value, dict):
        return {'dict': {k: _pack(v) for k, v in value.items()}}
    if value is None or type(value) in (str, int, bool, float):
        return value
    raise ValueError(f'Unsupported Target 6 snapshot value: {type(value).__name__}')


def _plain(value):
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {'tuple'}:
        return tuple(_plain(v) for v in value['tuple'])
    if set(value) == {'dict'}:
        return {k: _plain(v) for k, v in value['dict'].items()}
    if set(value) == {'scalar', 'value'}:
        constructors = {'Path': Path, 'UUID': UUID, 'datetime': datetime.fromisoformat, 'date': date.fromisoformat}
        return constructors[value['scalar']](value['value'])
    raise ValueError('Malformed untyped snapshot value')


@lru_cache(maxsize=None)
def _hints(cls):
    return get_type_hints(cls)


def _restore(value, expected):
    origin, arguments = get_origin(expected), get_args(expected)
    if origin in (UnionType, Union):
        matches = []
        for option in arguments:
            try:
                matches.append(_restore(value, option))
            except (ValueError, TypeError, KeyError):
                pass
        if len(matches) != 1:
            raise ValueError('Ambiguous or invalid snapshot union')
        return matches[0]
    if is_dataclass(expected):
        if not isinstance(value, dict) or set(value) != {f.name for f in fields(expected)}:
            raise ValueError(f'Invalid {expected.__name__} fields')
        return expected(**{name: _restore(value[name], kind) for name, kind in _hints(expected).items()})
    if origin in (tuple, list):
        values = value['tuple'] if origin is tuple and isinstance(value, dict) and set(value) == {'tuple'} else value
        if not isinstance(values, list):
            raise ValueError('Invalid snapshot sequence')
        if origin is tuple and len(arguments) != 2:
            if len(values) != len(arguments):
                raise ValueError('Invalid fixed tuple')
            return tuple(_restore(v, t) for v, t in zip(values, arguments))
        restored = [_restore(v, arguments[0]) for v in values]
        return tuple(restored) if origin is tuple else restored
    if expected is object:
        return _plain(value)
    if expected is dict or origin is dict:
        result = _plain(value)
        if type(result) is not dict:
            raise ValueError('Invalid snapshot dictionary')
        return result
    if isinstance(expected, type) and issubclass(expected, Enum):
        if not isinstance(value, dict) or set(value) != {'enum'}:
            raise ValueError('Invalid snapshot enum')
        return expected(value['enum'])
    if expected in (Path, UUID, datetime, date):
        result = _plain(value)
        if not isinstance(result, expected):
            raise ValueError('Snapshot scalar type mismatch')
        return result
    if expected in (str, int, bool, float, type(None)) and type(value) is expected:
        return value
    raise ValueError(f'Invalid snapshot field type: {expected}')


def _bytes(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate snapshot field')
        result[key] = value
    return result


def save_checkpoint(path: Path, value):
    if type(value) not in (FinalApprovalTargetOutput, MergePreconditionsOutput):
        raise ValueError('Only Target 6 Target / Ready checkpoints are supported')
    data = _pack(value)
    if _restore(data, type(value)) != value:
        raise ValueError('Target 6 checkpoint would lose existing DTO information')
    payload = {'version': 1, 'kind': 'target' if type(value) is FinalApprovalTargetOutput else 'ready', 'data': data}
    envelope = {'payload': payload, 'sha256': hashlib.sha256(_bytes(payload)).hexdigest()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(_bytes(envelope))
        stream.flush()
        os.fsync(stream.fileno())
    if load_checkpoint(path) != value:
        raise ValueError('Saved Target 6 checkpoint differs')


def load_checkpoint(path: Path):
    envelope = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique)
    if set(envelope) != {'payload', 'sha256'}:
        raise ValueError('Invalid Target 6 checkpoint envelope')
    payload = envelope['payload']
    if (set(payload) != {'version', 'kind', 'data'} or payload['version'] != 1
            or hashlib.sha256(_bytes(payload)).hexdigest() != envelope['sha256']):
        raise ValueError('Target 6 checkpoint integrity failure')
    root = {'target': FinalApprovalTargetOutput, 'ready': MergePreconditionsOutput}[payload['kind']]
    return _restore(payload['data'], root)
