from datetime import datetime
from pathlib import Path
import subprocess
from uuid import uuid4

from application.current_state_repository import load_current_state
from application.dto import (
    ExecuteImplementationInput,
    ExecuteImplementationOutput,
)
from application.implementation_result_parser import (
    ImplementationResultParseError,
    ImplementationResultParser,
)
from application.state_transition import transition_state
from core.approval_validation import validate_approval_result


def _git_working_tree_has_artifact_changes(
    working_directory: Path,
    *,
    state_file: Path,
    state_history_dir: Path,
) -> bool | None:
    try:
        completed = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            cwd=working_directory,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    ignored_paths: set[str] = set()

    for path in (state_file, state_history_dir):
        try:
            relative = path.resolve().relative_to(
                working_directory.resolve()
            )
        except ValueError:
            continue

        relative_text = relative.as_posix()
        ignored_paths.add(relative_text)
        ignored_paths.add(relative_text.rstrip("/") + "/")

    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue

        changed_path = line[3:].strip()

        if " -> " in changed_path:
            changed_path = changed_path.split(" -> ", 1)[1]

        changed_path = changed_path.strip('"').replace("\\\\", "/")

        if any(
            changed_path == ignored.rstrip("/")
            or changed_path.startswith(ignored)
            for ignored in ignored_paths
        ):
            continue

        return True

    return False


class ExecuteImplementationUseCase:
    def __init__(
        self,
        approval_repository,
        implementation_adapter,
    ) -> None:
        self._approval_repository = approval_repository
        self._implementation_adapter = implementation_adapter

    def execute(
        self,
        input_dto: ExecuteImplementationInput,
    ) -> ExecuteImplementationOutput:
        specification_record = self._approval_repository.get(
            input_dto.specification_approval_id
        )
        implementation_plan_record = self._approval_repository.get(
            input_dto.implementation_plan_approval_id
        )

        specification_validation = validate_approval_result(
            specification_record,
            str(input_dto.specification_path),
            "specification",
        )
        implementation_plan_validation = validate_approval_result(
            implementation_plan_record,
            str(input_dto.implementation_plan_path),
            "implementation_plan",
        )

        current_state = load_current_state(
            input_dto.state_file
        )["status"]

        if (
            not specification_validation.is_valid
            or not implementation_plan_validation.is_valid
        ):
            return ExecuteImplementationOutput(
                success=False,
                implementation_result=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state=current_state,
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Approval validation failed.",
            )

        if (
            input_dto.codex_prompt_specification_path
            != input_dto.specification_path
            or input_dto.codex_prompt_implementation_plan_path
            != input_dto.implementation_plan_path
        ):
            return ExecuteImplementationOutput(
                success=False,
                implementation_result=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state=current_state,
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason=(
                    "Codex Prompt correspondence validation failed."
                ),
            )

        if current_state != "implementation_ready":
            return ExecuteImplementationOutput(
                success=False,
                implementation_result=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state=current_state,
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Implementation is not ready.",
            )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementing",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Implementation execution started",
            },
        )

        try:
            raw_result = self._implementation_adapter.run(
                prompt=input_dto.codex_prompt,
                working_directory=input_dto.working_directory,
            )
        except Exception as exc:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state,
                    "to_state": "implementation_failed",
                    "occurred_at": (
                        datetime.now().astimezone().isoformat()
                    ),
                    "reason": "Implementation runner error",
                },
            )

            return ExecuteImplementationOutput(
                success=False,
                implementation_result=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state="implementation_failed",
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Implementation runner error.",
                error_message=str(exc),
            )

        try:
            implementation_result = ImplementationResultParser.parse(
                raw_result
            )
        except ImplementationResultParseError as exc:
            current_state = load_current_state(
                input_dto.state_file
            )["status"]

            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state,
                    "to_state": "implementation_failed",
                    "occurred_at": (
                        datetime.now().astimezone().isoformat()
                    ),
                    "reason": "Implementation result parse error",
                },
            )

            return ExecuteImplementationOutput(
                success=False,
                implementation_result=None,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state="implementation_failed",
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Implementation result parse error.",
                error_message=str(exc),
            )

        current_state = load_current_state(
            input_dto.state_file
        )["status"]

        if implementation_result.human_approval_required.strip() != "NONE":
            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state,
                    "to_state": "critical_approval_pending",
                    "occurred_at": (
                        datetime.now().astimezone().isoformat()
                    ),
                    "reason": "Human Approval required for critical change",
                },
            )

            return ExecuteImplementationOutput(
                success=False,
                implementation_result=implementation_result,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state="critical_approval_pending",
                technical_retry_required=False,
                critical_change_required=True,
                stop_reason="Human Approval required.",
            )

        if implementation_result.incomplete_items.strip() != "NONE":
            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state,
                    "to_state": "implementation_failed",
                    "occurred_at": (
                        datetime.now().astimezone().isoformat()
                    ),
                    "reason": "Implementation incomplete",
                },
            )

            return ExecuteImplementationOutput(
                success=False,
                implementation_result=implementation_result,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state="implementation_failed",
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Implementation incomplete.",
            )

        if implementation_result.test_execution_status == "ERROR":
            git_artifact_changes = (
                _git_working_tree_has_artifact_changes(
                    input_dto.working_directory,
                    state_file=input_dto.state_file,
                    state_history_dir=input_dto.state_history_dir,
                )
            )

            technical_retry_allowed = (
                implementation_result.technical_retry_safe is True
                and implementation_result.technical_retry_operation
                is not None
                and implementation_result.changed_files.strip() == "NONE"
                and git_artifact_changes is False
            )

            if technical_retry_allowed:
                try:
                    raw_result = self._implementation_adapter.run(
                        prompt=input_dto.codex_prompt,
                        working_directory=input_dto.working_directory,
                    )
                except Exception as exc:
                    transition_state(
                        input_dto.state_file,
                        input_dto.state_history_dir,
                        {
                            "transition_id": str(uuid4()),
                            "from_state": current_state,
                            "to_state": "implementation_failed",
                            "occurred_at": (
                                datetime.now().astimezone().isoformat()
                            ),
                            "reason": "Implementation runner error",
                        },
                    )

                    return ExecuteImplementationOutput(
                        success=False,
                        implementation_result=implementation_result,
                        specification_path=input_dto.specification_path,
                        implementation_plan_path=input_dto.implementation_plan_path,
                        implementation_branch=input_dto.implementation_branch,
                        base_commit=input_dto.base_commit,
                        specification_approval_validation_result=(
                            specification_validation
                        ),
                        implementation_plan_approval_validation_result=(
                            implementation_plan_validation
                        ),
                        current_state="implementation_failed",
                        technical_retry_required=False,
                        critical_change_required=False,
                        stop_reason="Implementation runner error.",
                        error_message=str(exc),
                    )

                try:
                    implementation_result = (
                        ImplementationResultParser.parse(raw_result)
                    )
                except ImplementationResultParseError as exc:
                    transition_state(
                        input_dto.state_file,
                        input_dto.state_history_dir,
                        {
                            "transition_id": str(uuid4()),
                            "from_state": current_state,
                            "to_state": "implementation_failed",
                            "occurred_at": (
                                datetime.now().astimezone().isoformat()
                            ),
                            "reason": "Implementation result parse error",
                        },
                    )

                    return ExecuteImplementationOutput(
                        success=False,
                        implementation_result=implementation_result,
                        specification_path=input_dto.specification_path,
                        implementation_plan_path=input_dto.implementation_plan_path,
                        implementation_branch=input_dto.implementation_branch,
                        base_commit=input_dto.base_commit,
                        specification_approval_validation_result=(
                            specification_validation
                        ),
                        implementation_plan_approval_validation_result=(
                            implementation_plan_validation
                        ),
                        current_state="implementation_failed",
                        technical_retry_required=False,
                        critical_change_required=False,
                        stop_reason="Implementation result parse error.",
                        error_message=str(exc),
                    )

                current_state = load_current_state(
                    input_dto.state_file
                )["status"]

                if (
                    implementation_result.human_approval_required.strip()
                    != "NONE"
                ):
                    transition_state(
                        input_dto.state_file,
                        input_dto.state_history_dir,
                        {
                            "transition_id": str(uuid4()),
                            "from_state": current_state,
                            "to_state": "critical_approval_pending",
                            "occurred_at": (
                                datetime.now().astimezone().isoformat()
                            ),
                            "reason": "Human Approval required",
                        },
                    )

                    return ExecuteImplementationOutput(
                        success=False,
                        implementation_result=implementation_result,
                        specification_path=input_dto.specification_path,
                        implementation_plan_path=input_dto.implementation_plan_path,
                        implementation_branch=input_dto.implementation_branch,
                        base_commit=input_dto.base_commit,
                        specification_approval_validation_result=(
                            specification_validation
                        ),
                        implementation_plan_approval_validation_result=(
                            implementation_plan_validation
                        ),
                        current_state="critical_approval_pending",
                        technical_retry_required=False,
                        critical_change_required=True,
                        stop_reason="Human Approval required.",
                    )

                if implementation_result.incomplete_items.strip() != "NONE":
                    transition_state(
                        input_dto.state_file,
                        input_dto.state_history_dir,
                        {
                            "transition_id": str(uuid4()),
                            "from_state": current_state,
                            "to_state": "implementation_failed",
                            "occurred_at": (
                                datetime.now().astimezone().isoformat()
                            ),
                            "reason": "Implementation incomplete",
                        },
                    )

                    return ExecuteImplementationOutput(
                        success=False,
                        implementation_result=implementation_result,
                        specification_path=input_dto.specification_path,
                        implementation_plan_path=input_dto.implementation_plan_path,
                        implementation_branch=input_dto.implementation_branch,
                        base_commit=input_dto.base_commit,
                        specification_approval_validation_result=(
                            specification_validation
                        ),
                        implementation_plan_approval_validation_result=(
                            implementation_plan_validation
                        ),
                        current_state="implementation_failed",
                        technical_retry_required=False,
                        critical_change_required=False,
                        stop_reason="Implementation incomplete.",
                    )

            if implementation_result.test_execution_status == "ERROR":
                transition_state(
                    input_dto.state_file,
                    input_dto.state_history_dir,
                    {
                        "transition_id": str(uuid4()),
                        "from_state": current_state,
                        "to_state": "implementation_failed",
                        "occurred_at": (
                            datetime.now().astimezone().isoformat()
                        ),
                        "reason": "Implementation test execution error",
                    },
                )

                return ExecuteImplementationOutput(
                    success=False,
                    implementation_result=implementation_result,
                    specification_path=input_dto.specification_path,
                    implementation_plan_path=(
                        input_dto.implementation_plan_path
                    ),
                    implementation_branch=input_dto.implementation_branch,
                    base_commit=input_dto.base_commit,
                    specification_approval_validation_result=(
                        specification_validation
                    ),
                    implementation_plan_approval_validation_result=(
                        implementation_plan_validation
                    ),
                    current_state="implementation_failed",
                    technical_retry_required=False,
                    critical_change_required=False,
                    stop_reason="Test execution error.",
                )

        if implementation_result.errors.strip() != "NONE":
            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state,
                    "to_state": "implementation_failed",
                    "occurred_at": (
                        datetime.now().astimezone().isoformat()
                    ),
                    "reason": "Implementation error reported",
                },
            )

            return ExecuteImplementationOutput(
                success=False,
                implementation_result=implementation_result,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state="implementation_failed",
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Implementation error reported.",
            )

        if (
            implementation_result.test_required
            and implementation_result.test_execution_status == "NOT_RUN"
        ):
            transition_state(
                input_dto.state_file,
                input_dto.state_history_dir,
                {
                    "transition_id": str(uuid4()),
                    "from_state": current_state,
                    "to_state": "implementation_failed",
                    "occurred_at": (
                        datetime.now().astimezone().isoformat()
                    ),
                    "reason": "Required tests were not run",
                },
            )

            return ExecuteImplementationOutput(
                success=False,
                implementation_result=implementation_result,
                specification_path=input_dto.specification_path,
                implementation_plan_path=input_dto.implementation_plan_path,
                implementation_branch=input_dto.implementation_branch,
                base_commit=input_dto.base_commit,
                specification_approval_validation_result=(
                    specification_validation
                ),
                implementation_plan_approval_validation_result=(
                    implementation_plan_validation
                ),
                current_state="implementation_failed",
                technical_retry_required=False,
                critical_change_required=False,
                stop_reason="Required tests were not run.",
            )

        transition_state(
            input_dto.state_file,
            input_dto.state_history_dir,
            {
                "transition_id": str(uuid4()),
                "from_state": current_state,
                "to_state": "implementation_completed",
                "occurred_at": datetime.now().astimezone().isoformat(),
                "reason": "Implementation execution completed",
            },
        )

        return ExecuteImplementationOutput(
            success=True,
            implementation_result=implementation_result,
            specification_path=input_dto.specification_path,
            implementation_plan_path=input_dto.implementation_plan_path,
            implementation_branch=input_dto.implementation_branch,
            base_commit=input_dto.base_commit,
            specification_approval_validation_result=(
                specification_validation
            ),
            implementation_plan_approval_validation_result=(
                implementation_plan_validation
            ),
            current_state="implementation_completed",
            technical_retry_required=False,
            critical_change_required=False,
        )
