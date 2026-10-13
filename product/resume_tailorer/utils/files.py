"""Reading files that another thread or process replaces with os.replace.

On Windows, opening a file at the instant os.replace swaps it raises PermissionError, even though
the replace itself is atomic. Readers that treated that as "missing" briefly lost the saved
review, the batch or the run status (2026-10-12). A short retry reads the old or the new file.
"""

from __future__ import annotations

import time
from pathlib import Path

_ATTEMPTS = 20
_PAUSE_SECONDS = 0.01


def read_text_retrying(path: str | Path, encoding: str = "utf-8") -> str:
    """Path.read_text, retrying only Windows' brief replace contention; other errors propagate."""
    for attempt in range(_ATTEMPTS):
        try:
            return Path(path).read_text(encoding=encoding)
        except PermissionError:
            if attempt == _ATTEMPTS - 1:
                raise
            time.sleep(_PAUSE_SECONDS)
    raise AssertionError("unreachable")
