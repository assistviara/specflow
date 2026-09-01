import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from application.dto import (
    GenerateImplementationPlanInput,
    GenerateImplementationPlanOutput,
)
from application.generate_implementation_plan import (
    GenerateImplementationPlanUseCase,
)
from core.ai.ai_request import AIRequest
from core.ai.ai_response import AIResponse
from core.prompt_builder import PromptResult



def test_invalid_specification_approval_does_not_start_plan_generation(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "# Specification",
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "specification_ready"}',
        encoding="utf-8",
    )

    history_dir = tmp_path / "state_history"

    plan_prompt_generator = Mock()
    ai_service = Mock()

    use_case = GenerateImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = GenerateImplementationPlanInput(
        constitution_path=tmp_path / "constitution.md",
        principles_path=tmp_path / "principles.md",
        specification_path=specification_path,
        specification_approval={
            "approval_id": "approval-001",
            "artifact_type": "specification",
            "artifact_path": str(specification_path),
            "artifact_hash": "invalid-hash",
            "decision": "approved",
            "approved_at": "2026-09-01T00:00:00",
            "comment": "",
        },
        decisions_path=tmp_path / "decisions.md",
        implementation_plan_template_path=(
            tmp_path / "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=tmp_path / "plan_prompt.md",
        state_file=state_file,
        state_history_dir=history_dir,
    )

    result = use_case.execute(input_dto)

    assert result is None
    assert '"status": "specification_ready"' in state_file.read_text(
        encoding="utf-8"
    )
    plan_prompt_generator.generate.assert_not_called()
    ai_service.run.assert_not_called()



def test_valid_specification_approval_transitions_to_plan_generating(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "# Specification",
        encoding="utf-8",
    )

    specification_hash = hashlib.sha256(
        specification_path.read_bytes()
    ).hexdigest()

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "specification_ready"}',
        encoding="utf-8",
    )

    history_dir = tmp_path / "state_history"

    plan_prompt_generator = Mock()
    plan_prompt_generator.generate.return_value = PromptResult(
        content="Generate Implementation Plan",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    ai_service = Mock()

    use_case = GenerateImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = GenerateImplementationPlanInput(
        constitution_path=tmp_path / "constitution.md",
        principles_path=tmp_path / "principles.md",
        specification_path=specification_path,
        specification_approval={
            "approval_id": "approval-001",
            "artifact_type": "specification",
            "artifact_path": str(specification_path),
            "artifact_hash": specification_hash,
            "decision": "approved",
            "approved_at": "2026-09-01T00:00:00+09:00",
            "comment": "",
        },
        decisions_path=tmp_path / "decisions.md",
        implementation_plan_template_path=(
            tmp_path / "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=tmp_path / "plan_prompt.md",
        state_file=state_file,
        state_history_dir=history_dir,
    )

    use_case.execute(input_dto)

    


    history_files = list(history_dir.glob("*.json"))
    assert len(history_files) == 2

    transitions = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in history_files
    ]

    transition = next(
        transition
        for transition in transitions
        if transition["from_state"] == "specification_ready"
        and transition["to_state"] == "plan_generating"
    )

    assert transition["reason"] == (
        "Implementation Plan generation started"
    )
    assert transition["transition_id"]
    assert transition["occurred_at"]

def test_valid_specification_approval_calls_plan_prompt_generator(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "# Specification",
        encoding="utf-8",
    )

    specification_hash = hashlib.sha256(
        specification_path.read_bytes()
    ).hexdigest()

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "specification_ready"}',
        encoding="utf-8",
    )

    history_dir = tmp_path / "state_history"

    plan_prompt_generator = Mock()
    plan_prompt_generator.generate.return_value = PromptResult(
        content="Generate Implementation Plan",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    ai_service = Mock()

    use_case = GenerateImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = GenerateImplementationPlanInput(
        constitution_path=tmp_path / "constitution.md",
        principles_path=tmp_path / "principles.md",
        specification_path=specification_path,
        specification_approval={
            "approval_id": "approval-001",
            "artifact_type": "specification",
            "artifact_path": str(specification_path),
            "artifact_hash": specification_hash,
            "decision": "approved",
            "approved_at": "2026-09-01T00:00:00+09:00",
            "comment": "",
        },
        decisions_path=tmp_path / "decisions.md",
        implementation_plan_template_path=(
            tmp_path / "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=tmp_path / "plan_prompt.md",
        state_file=state_file,
        state_history_dir=history_dir,
    )

    use_case.execute(input_dto)

    plan_prompt_generator.generate.assert_called_once_with(
        constitution_path=input_dto.constitution_path,
        principles_path=input_dto.principles_path,
        specification_path=input_dto.specification_path,
        decisions_path=input_dto.decisions_path,
        implementation_plan_template_path=(
            input_dto.implementation_plan_template_path
        ),
        project_metadata=input_dto.project_metadata,
        template_path=input_dto.template_path,
    )



def test_plan_prompt_result_is_converted_to_ai_request(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "# Specification",
        encoding="utf-8",
    )

    specification_hash = hashlib.sha256(
        specification_path.read_bytes()
    ).hexdigest()

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "specification_ready"}',
        encoding="utf-8",
    )

    history_dir = tmp_path / "state_history"

    prompt_result = PromptResult(
        content="Generate Implementation Plan",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    plan_prompt_generator = Mock()
    plan_prompt_generator.generate.return_value = prompt_result

    ai_service = Mock()

    use_case = GenerateImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = GenerateImplementationPlanInput(
        constitution_path=tmp_path / "constitution.md",
        principles_path=tmp_path / "principles.md",
        specification_path=specification_path,
        specification_approval={
            "approval_id": "approval-001",
            "artifact_type": "specification",
            "artifact_path": str(specification_path),
            "artifact_hash": specification_hash,
            "decision": "approved",
            "approved_at": "2026-09-01T00:00:00+09:00",
            "comment": "",
        },
        decisions_path=tmp_path / "decisions.md",
        implementation_plan_template_path=(
            tmp_path / "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=tmp_path / "plan_prompt.md",
        state_file=state_file,
        state_history_dir=history_dir,
    )

    use_case.execute(input_dto)

    ai_service.run.assert_called_once()

    request = ai_service.run.call_args.args[0]

    assert isinstance(request, AIRequest)
    assert request.prompt == "Generate Implementation Plan"

def test_failed_ai_response_does_not_transition_to_plan_approval_pending(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "# Specification",
        encoding="utf-8",
    )

    specification_hash = hashlib.sha256(
        specification_path.read_bytes()
    ).hexdigest()

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "specification_ready"}',
        encoding="utf-8",
    )

    history_dir = tmp_path / "state_history"

    prompt_result = PromptResult(
        content="Generate Implementation Plan",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    plan_prompt_generator = Mock()
    plan_prompt_generator.generate.return_value = prompt_result

    ai_service = Mock()
    ai_service.run.return_value = AIResponse(
        content="",
        success=False,
        error_message="Plan generation failed",
    )

    use_case = GenerateImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = GenerateImplementationPlanInput(
        constitution_path=tmp_path / "constitution.md",
        principles_path=tmp_path / "principles.md",
        specification_path=specification_path,
        specification_approval={
            "approval_id": "approval-001",
            "artifact_type": "specification",
            "artifact_path": str(specification_path),
            "artifact_hash": specification_hash,
            "decision": "approved",
            "approved_at": "2026-09-01T00:00:00+09:00",
            "comment": "",
        },
        decisions_path=tmp_path / "decisions.md",
        implementation_plan_template_path=(
            tmp_path / "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=tmp_path / "plan_prompt.md",
        state_file=state_file,
        state_history_dir=history_dir,
    )

    output = use_case.execute(input_dto)

    assert output.success is False
    assert output.implementation_plan_draft is None
    assert output.specification_path == specification_path
    assert output.error_message == "Plan generation failed"

    current_state = json.loads(
        state_file.read_text(encoding="utf-8")
    )

    assert current_state["status"] == "plan_generating"

    history_files = list(history_dir.glob("*.json"))
    assert len(history_files) == 1

def test_successful_ai_response_returns_implementation_plan_draft(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "# Specification",
        encoding="utf-8",
    )

    specification_hash = hashlib.sha256(
        specification_path.read_bytes()
    ).hexdigest()

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "specification_ready"}',
        encoding="utf-8",
    )

    history_dir = tmp_path / "state_history"

    prompt_result = PromptResult(
        content="Generate Implementation Plan",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    plan_prompt_generator = Mock()
    plan_prompt_generator.generate.return_value = prompt_result

    ai_service = Mock()
    ai_service.run.return_value = AIResponse(
        content="# Implementation Plan Draft",
        success=True,
    )

    use_case = GenerateImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = GenerateImplementationPlanInput(
        constitution_path=tmp_path / "constitution.md",
        principles_path=tmp_path / "principles.md",
        specification_path=specification_path,
        specification_approval={
            "approval_id": "approval-001",
            "artifact_type": "specification",
            "artifact_path": str(specification_path),
            "artifact_hash": specification_hash,
            "decision": "approved",
            "approved_at": "2026-09-01T00:00:00+09:00",
            "comment": "",
        },
        decisions_path=tmp_path / "decisions.md",
        implementation_plan_template_path=(
            tmp_path / "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=tmp_path / "plan_prompt.md",
        state_file=state_file,
        state_history_dir=history_dir,
    )

    result = use_case.execute(input_dto)

    assert isinstance(
        result,
        GenerateImplementationPlanOutput,
    )
    assert (
        result.implementation_plan_draft
        == "# Implementation Plan Draft"
    )
    assert result.specification_path == specification_path

def test_successful_plan_generation_transitions_to_plan_approval_pending(
    tmp_path: Path,
):
    specification_path = tmp_path / "specification.md"
    specification_path.write_text(
        "# Specification",
        encoding="utf-8",
    )

    specification_hash = hashlib.sha256(
        specification_path.read_bytes()
    ).hexdigest()

    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"status": "specification_ready"}',
        encoding="utf-8",
    )

    history_dir = tmp_path / "state_history"

    prompt_result = PromptResult(
        content="Generate Implementation Plan",
        undefined_variables=[],
        unused_context=[],
        warnings=[],
    )

    plan_prompt_generator = Mock()
    plan_prompt_generator.generate.return_value = prompt_result

    ai_service = Mock()
    ai_service.run.return_value = AIResponse(
        content="# Implementation Plan Draft",
        success=True,
    )

    use_case = GenerateImplementationPlanUseCase(
        plan_prompt_generator=plan_prompt_generator,
        ai_service=ai_service,
    )

    input_dto = GenerateImplementationPlanInput(
        constitution_path=tmp_path / "constitution.md",
        principles_path=tmp_path / "principles.md",
        specification_path=specification_path,
        specification_approval={
            "approval_id": "approval-001",
            "artifact_type": "specification",
            "artifact_path": str(specification_path),
            "artifact_hash": specification_hash,
            "decision": "approved",
            "approved_at": "2026-09-01T00:00:00+09:00",
            "comment": "",
        },
        decisions_path=tmp_path / "decisions.md",
        implementation_plan_template_path=(
            tmp_path / "implementation_plan_template.md"
        ),
        project_metadata={"project_name": "specflow"},
        template_path=tmp_path / "plan_prompt.md",
        state_file=state_file,
        state_history_dir=history_dir,
    )

    use_case.execute(input_dto)

    history_files = list(history_dir.glob("*.json"))
    assert len(history_files) == 2

    transitions = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in history_files
    ]

    assert any(
        transition["from_state"] == "specification_ready"
        and transition["to_state"] == "plan_generating"
        and transition["reason"]
        == "Implementation Plan generation started"
        for transition in transitions
    )

    transitions = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in history_files
    ]

    assert any(
        transition["from_state"] == "plan_generating"
        and transition["to_state"] == "plan_approval_pending"
        and transition["reason"]
        == "Implementation Plan Draft generated"
        for transition in transitions
    )