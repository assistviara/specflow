import json
from pathlib import Path


def save_state_transition_history(
    history_dir: Path,
    transition: dict,
) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)

    transition_id = transition["transition_id"]
    history_file = history_dir / f"{transition_id}.json"

    history_file.write_text(
        json.dumps(transition, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )