"""Shared Streamlit shell: the six-destination rail and per-page headers (spec 007)."""

from __future__ import annotations

from html import escape
from typing import Iterable, Optional

from resume_tailorer.ui.design_system import DESTINATIONS, THEME_CSS, ProgressStep

ACTIVE_JOB_KEY = "pending_tailor_job"


def _rail_profile_line(session) -> str:
    from resume_tailorer.ui.profile_readiness import readiness_line

    return readiness_line(session)


def render_app_shell(active: str, _legacy_state: Optional[Iterable] = None) -> None:
    """Theme, the navigation rail, identity, readiness and the active job."""
    import streamlit as st

    st.markdown(THEME_CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(
            '<div class="jc-brand"><strong>Job Copilot</strong>'
            "<span>Truthful resumes, real jobs, no guesswork</span></div>",
            unsafe_allow_html=True,
        )
        for destination in DESTINATIONS:
            st.page_link(destination.path, label=destination.name, icon=destination.icon)

        blocks = [f"<strong>Profile</strong>{escape(_rail_profile_line(st.session_state))}"]
        job = st.session_state.get(ACTIVE_JOB_KEY) or {}
        if job.get("title"):
            blocks.append(
                f"<strong>Working on</strong>{escape(job.get('title', ''))} · {escape(job.get('company', ''))}"
            )
        for block in blocks:
            st.markdown(f'<div class="jc-rail-block">{block}</div>', unsafe_allow_html=True)

        identity = st.session_state.get("identity_view") or {}
        st.markdown('<div class="jc-rail-block"></div>', unsafe_allow_html=True)
        if identity.get("signed_in"):
            st.caption(f"Signed in as {identity.get('name', '')}")
            st.button("Sign out", on_click=st.logout, key="jc_sign_out")
        else:
            st.warning("Local demo: everyone using this address shares one workspace. Don't share this link.")
        st.caption("Job Copilot only uses facts you've confirmed and never submits for you.")
    st.session_state["jc_active_destination"] = active


def render_page_header(title: str, description: str, action_label: str | None = None) -> bool:
    """A consistent page introduction and optional primary action."""
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


def render_progress(steps: Iterable[ProgressStep], label: str) -> None:
    """A page's own progress strip (replaces the old global ribbon)."""
    import streamlit as st

    items = "".join(
        f'<div class="jc-step {escape(step.state)}" role="listitem">{escape(step.label)}'
        f'<span class="jc-sr-only"> — {escape(step.state)}</span></div>'
        for step in steps
    )
    st.markdown(f'<div class="jc-progress" role="list" aria-label="{escape(label)}">{items}</div>', unsafe_allow_html=True)


def primary_action(label: str, page: str, key: str, before=None) -> None:
    """The one dominant action of a region: a primary button that opens a destination.
    `before` runs first, e.g. to hand the destination the job it should open."""
    import streamlit as st

    if st.button(label, type="primary", key=key):
        if before is not None:
            before()
        st.switch_page(page)


def chip(text: str, tone: str = "") -> str:
    return f'<span class="jc-chip {escape(tone)}">{escape(text)}</span>'
