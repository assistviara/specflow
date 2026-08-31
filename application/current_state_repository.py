import json
from pathlib import Path


def load_current_state(state_file: Path) -> dict:
    return json.loads(state_file.read_text(encoding="utf-8"))


def save_current_state(state_file: Path, state: dict) -> None:
    state_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )