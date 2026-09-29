"""Shared presentation layer for Job Copilot's Streamlit workspaces."""

from resume_tailorer.ui.design_system import (
    WORKSPACES,
    build_workflow_state,
    display_optional,
    semantic_status,
)
from resume_tailorer.ui.shell import render_app_shell, render_page_header

__all__ = [
    "WORKSPACES",
    "build_workflow_state",
    "display_optional",
    "render_app_shell",
    "render_page_header",
    "semantic_status",
]
