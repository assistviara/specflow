from pathlib import Path

from application.state_transition_history import save_state_transition_history


def test_save_state_transition_history_writes_one_json_file(tmp_path: Path):
    history_dir = tmp_path / "state_history"

    transition = {
        "transition_id": "transition-001",
        "from_state": "specification_editing",
        "to_state": "implementation_planning",
        "occurred_at": "2026-08-31T12:00:00+09:00",
        "reason": "Human approved the specification.",
    }

    save_state_transition_history(history_dir, transition)

    history_file = history_dir / "transition-001.json"

    assert history_file.exists()

    saved_transition = __import__("json").loads(
     history_file.read_text(encoding="utf-8")
    )

    assert saved_transition == transition