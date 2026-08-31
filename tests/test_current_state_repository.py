from pathlib import Path

from application.current_state_repository import (
    load_current_state,
    save_current_state,
)



def test_load_current_state_returns_existing_state_as_dict(tmp_path: Path):
    state_file = tmp_path / "state.json"
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

    state = load_current_state(state_file)

    assert state == {
        "status": "specification_editing",
        "plan_approved": False,
        "repair_count": 0,
        "last_result": None,
    }



def test_save_current_state_writes_state_as_json(tmp_path: Path):
    state_file = tmp_path / "state.json"

    state = {
        "status": "implementation_planning",
        "plan_approved": True,
        "repair_count": 1,
        "last_result": "ok",
    }

    save_current_state(state_file, state)

    assert load_current_state(state_file) == state