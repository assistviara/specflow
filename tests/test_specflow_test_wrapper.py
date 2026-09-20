import subprocess
import sys


def test_wrapper_runs_child_command_and_returns_its_exit_code():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "infrastructure.specflow_test_wrapper",
            "--phase",
            "target",
            "--",
            sys.executable,
            "-c",
            "print('WRAPPER_OK')",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "WRAPPER_OK"
    assert result.stderr == ""



def test_wrapper_preserves_child_command_failure():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "infrastructure.specflow_test_wrapper",
            "--phase",
            "initial",
            "--",
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('EXPECTED_FAILURE'); "
                "sys.exit(7)"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 7
    assert result.stdout.strip() == "EXPECTED_FAILURE"
    assert result.stderr == ""
