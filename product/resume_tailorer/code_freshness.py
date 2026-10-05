"""Pick up newly deployed code without a manual reboot (decision 027).

After a push, Streamlit Community Cloud pulls the new files and reruns the page
script, but modules already imported (everything under `resume_tailorer`) stay
in memory, so pages mixed new page code with old shared code until the app was
rebooted. The package's files are fingerprinted when this module is imported;
when the files on disk no longer match, the package's modules are dropped from
`sys.modules` so the next run imports the new code. No Streamlit import.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGE = "resume_tailorer"
_ROOT = Path(__file__).resolve().parent


def fingerprint(root: Path = _ROOT) -> tuple:
    """(relative path, size, mtime) of every Python file in the package. Cheap: stat only."""
    items = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        items.append((str(path.relative_to(root)), stat.st_size, stat.st_mtime_ns))
    return tuple(items)


_LOADED = fingerprint()
# Identifies the code this process is running. Each session records the version it last ran
# on: a session that outlives a reload (another session triggered it) still holds objects
# made by the old classes, and plain Enums from two module copies never compare equal.
CODE_VERSION = str(hash(_LOADED))
SESSION_KEY = "_job_copilot_code_version"


def code_changed_on_disk() -> bool:
    return fingerprint() != _LOADED


def drop_stale_modules(modules: dict | None = None) -> int:
    """Forget every `resume_tailorer` module so the next import reads the new files."""
    modules = sys.modules if modules is None else modules
    stale = [name for name in modules if name == _PACKAGE or name.startswith(_PACKAGE + ".")]
    for name in stale:
        modules.pop(name, None)
    return len(stale)
