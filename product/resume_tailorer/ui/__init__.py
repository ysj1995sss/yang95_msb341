"""Shared view logic for the website's backend (no Streamlit since spec 021)."""

from resume_tailorer.ui.design_system import (
    DESTINATIONS,
    WORKSPACES,
    display_optional,
    progress_steps,
    semantic_status,
)

__all__ = [
    "DESTINATIONS",
    "WORKSPACES",
    "display_optional",
    "progress_steps",
    "semantic_status",
]
