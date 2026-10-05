"""Our CSS styles Streamlit through its internal test ids and class names, which can change
between Streamlit releases (decision 027). Streamlit is pinned; this fails loudly if an
upgrade removes a hook the theme depends on, instead of the styling silently breaking."""

import re
from functools import lru_cache
from pathlib import Path

import pytest
import streamlit

from resume_tailorer.ui.design_system import THEME_CSS

_HOOKS = re.compile(r'data-testid[*^]?=["\']?([A-Za-z]+)|\.(st[A-Z][A-Za-z]+)\b')


@lru_cache(maxsize=1)
def _frontend() -> str:
    static = Path(streamlit.__file__).parent / "static"
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in static.rglob("*.js"))


def _hooks() -> list[str]:
    return sorted({a or b for a, b in _HOOKS.findall(THEME_CSS)})


def test_the_theme_uses_some_streamlit_hooks():
    assert len(_hooks()) >= 5


@pytest.mark.parametrize("hook", _hooks())
def test_each_hook_exists_in_the_installed_streamlit(hook):
    assert hook in _frontend(), (
        f"Streamlit {streamlit.__version__} no longer has '{hook}'. Update ui/design_system.py "
        "before upgrading Streamlit (see decision 027)."
    )
