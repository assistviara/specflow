from pathlib import Path

from application.current_state_repository import (
    load_current_state,
    save_current_state,
)
from application.state_transition_history import (
    save_state_transition_history,
)


def transition_state(
    state_file: Path,
    history_dir: Path,
    transition: dict,
) -> None:
    current_state = load_current_state(state_file)
    current_state["status"] = transition["to_state"]

    save_current_state(state_file, current_state)
    save_state_transition_history(history_dir, transition)