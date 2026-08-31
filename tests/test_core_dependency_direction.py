from pathlib import Path


def test_core_does_not_depend_on_application():
    core_dir = Path("core")

    for python_file in core_dir.rglob("*.py"):
        source = python_file.read_text(encoding="utf-8")

        assert "import application" not in source
        assert "from application" not in source