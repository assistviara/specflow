from pathlib import Path

from application.state_transition import transition_state
from application.current_state_repository import load_current_state


def test_transition_state_updates_current_state_and_records_history(tmp_path: Path):
    state_file = tmp_path / "state.json"
    history_dir = tmp_path / "state_history"

    state_file.write_text(
        """
{
  "status": "specification_editing",
  "plan_approved": false,
  "repair_count": 0,
  "last_result": null
}
""".strip(),
        encoding="utf-8",
    )

    transition = {
        "transition_id": "transition-001",
        "from_state": "specification_editing",
        "to_state": "implementation_planning",
        "occurred_at": "2026-08-31T12:00:00+09:00",
        "reason": "Human approved the specification.",
    }

    transition_state(
        state_file=state_file,
        history_dir=history_dir,
        transition=transition,
    )

    current_state = load_current_state(state_file)

    assert current_state["status"] == "implementation_planning"
    assert (history_dir / "transition-001.json").exists()