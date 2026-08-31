from dataclasses import FrozenInstanceError

import pytest

from application.dto import InputDTO, OutputDTO


def test_input_dto_is_frozen_dataclass():
    dto = InputDTO()

    with pytest.raises(FrozenInstanceError):
        dto.some_value = "changed"


def test_output_dto_is_frozen_dataclass():
    dto = OutputDTO()

    with pytest.raises(FrozenInstanceError):
        dto.some_value = "changed"