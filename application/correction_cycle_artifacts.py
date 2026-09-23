import hashlib
import subprocess
from pathlib import Path


def snapshot_artifacts(root: Path) -> dict[str, str]:
    """Observe tracked and nonignored files, including preexisting dirty work."""
    result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            cwd=root, check=True, capture_output=True)
    values = {}
    for name in result.stdout.decode('utf-8').split('\0'):
        if not name:
            continue
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Artifact path escapes repository')
        if path.is_file():
            values[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values
