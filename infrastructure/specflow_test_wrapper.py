import argparse
import subprocess
from collections.abc import Sequence


VALID_PHASES = (
    "initial",
    "target",
    "full",
)


def _parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a test command with an explicit "
            "SpecFlow Test phase."
        )
    )
    parser.add_argument(
        "--phase",
        required=True,
        choices=VALID_PHASES,
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
    )

    parsed = parser.parse_args(arguments)

    if (
        parsed.command
        and parsed.command[0] == "--"
    ):
        parsed.command = parsed.command[1:]

    if not parsed.command:
        parser.error(
            "a child test command is required "
            "after --"
        )

    return parsed


def main(
    arguments: Sequence[str] | None = None,
) -> int:
    parsed = _parse_arguments(arguments)

    result = subprocess.run(
        parsed.command,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
