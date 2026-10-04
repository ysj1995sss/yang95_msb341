"""Shared presentation layer for Job Copilot's Streamlit destinations."""

from resume_tailorer.ui.design_system import (
    DESTINATIONS,
    WORKSPACES,
    display_optional,
    progress_steps,
    semantic_status,
)
from resume_tailorer.ui.shell import chip, render_app_shell, render_page_header, render_progress

__all__ = [
    "DESTINATIONS",
    "WORKSPACES",
    "chip",
    "display_optional",
    "progress_steps",
    "render_app_shell",
    "render_page_header",
    "render_progress",
    "semantic_status",
]
