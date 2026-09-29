"""Shared Streamlit shell for the five Job Copilot workspaces."""

from __future__ import annotations

from html import escape
from typing import Iterable

from resume_tailorer.ui.design_system import THEME_CSS, WORKSPACES, WorkflowStep


def render_app_shell(active: str, workflow_state: Iterable[WorkflowStep]) -> None:
    import streamlit as st

    st.markdown(THEME_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(
            '<div class="jc-brand"><strong>Job Copilot</strong>'
            '<span>Evidence-first application workspace</span></div>',
            unsafe_allow_html=True,
        )
        for workspace in WORKSPACES:
            st.page_link(
                workspace.path,
                label=(f"→ {workspace.name}" if workspace.name == active else workspace.name),
            )
        st.caption("Your facts stay separate from job requirements.")

    steps = "".join(
        f'<div class="jc-step {escape(step.state)}">{escape(step.label)}'
        f'<span class="jc-sr-only"> — {escape(step.state)}</span></div>'
        for step in workflow_state
    )
    st.markdown(f'<div class="jc-ribbon" aria-label="Application progress">{steps}</div>', unsafe_allow_html=True)


def render_page_header(title: str, description: str, action_label: str | None = None) -> bool:
    """Render a consistent page introduction and optional primary action."""
    import streamlit as st

    if action_label:
        copy, action = st.columns([4, 1])
    else:
        copy, action = st.container(), None
    with copy:
        st.markdown(
            f'<header class="jc-page-header"><h1>{escape(title)}</h1><p>{escape(description)}</p></header>',
            unsafe_allow_html=True,
        )
    return bool(action.button(action_label, type="primary", use_container_width=True)) if action else False
