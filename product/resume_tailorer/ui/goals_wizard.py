"""Streamlit rendering of the one-question-at-a-time goals wizard.

Shared by Home (first-time setup) and Career Profile (editing goals). Logic
lives in ui/onboarding.py.
"""

from __future__ import annotations

from html import escape

from resume_tailorer.job_search.job_attributes import EXPERIENCE_LEVEL_OPTIONS, INDUSTRY_OPTIONS
from resume_tailorer.ui.onboarding import (
    WIZARD_DRAFT_KEY,
    WIZARD_STEP_KEY,
    WIZARD_STEPS,
    WORK_MODE_LABELS,
    WORK_MODES,
    YES_NO_LATER,
    answer_to_bool,
    bool_to_answer,
    draft_from_record,
    save_goals,
    step_valid,
    suggested_titles,
)


def render_goals_wizard(owner_id: str, on_done_label: str = "Save my goals") -> bool:
    """Render the current question. Returns True on the run where goals were saved."""
    import streamlit as st

    from resume_tailorer.profile_import import RECORD_KEY, save_record

    record = st.session_state.get(RECORD_KEY) or {}
    goals = st.session_state.setdefault(WIZARD_DRAFT_KEY, draft_from_record(record))
    step_no = min(st.session_state.setdefault(WIZARD_STEP_KEY, 0), len(WIZARD_STEPS) - 1)
    step = WIZARD_STEPS[step_no]

    st.markdown(
        f'<div class="jc-meta">Question {step_no + 1} of {len(WIZARD_STEPS)}</div>', unsafe_allow_html=True
    )
    st.progress((step_no + 1) / len(WIZARD_STEPS))
    st.markdown(f"### {escape(step.title)}")
    st.caption(step.help)
    key = f"wiz_{step.key}"

    if step.key == "job_title":
        suggestions = suggested_titles(record.get("profile"))
        if suggestions:
            st.caption("From your resume:")
            cols = st.columns(len(suggestions))
            for col, title in zip(cols, suggestions):
                if col.button(title, key=f"wiz_suggest_{title}", use_container_width=True):
                    goals["job_title"] = title
                    st.session_state[key] = title
        st.session_state.setdefault(key, goals.get("job_title", ""))
        goals["job_title"] = st.text_input("Job title", key=key, placeholder="e.g. Product Marketing Manager")
    elif step.key == "location":
        st.session_state.setdefault(key, goals.get("location", ""))
        st.session_state.setdefault("wiz_relocation", bool(goals.get("relocation_willing")))
        goals["location"] = st.text_input("Location", key=key, placeholder="e.g. Salt Lake City, UT")
        goals["relocation_willing"] = st.checkbox("I'm open to relocating", key="wiz_relocation")
    elif step.key == "remote_preference":
        current = goals.get("remote_preference") or "any"
        goals["remote_preference"] = st.radio(
            "Work mode", WORK_MODES, index=WORK_MODES.index(current) if current in WORK_MODES else 0,
            format_func=WORK_MODE_LABELS.get, key=key, horizontal=True,
        )
    elif step.key == "experience_level":
        goals["experience_level"] = st.multiselect(
            "Level", EXPERIENCE_LEVEL_OPTIONS, default=[v for v in goals.get("experience_level") or [] if v in EXPERIENCE_LEVEL_OPTIONS], key=key
        )
    elif step.key == "min_salary":
        st.session_state.setdefault(key, int(goals.get("min_salary") or 0))
        goals["min_salary"] = st.number_input(
            "Minimum yearly salary (USD)", min_value=0, max_value=1_000_000, step=5000, key=key,
        )
    elif step.key == "industries":
        goals["industries"] = st.multiselect(
            "Industries", INDUSTRY_OPTIONS, default=[v for v in goals.get("industries") or [] if v in INDUSTRY_OPTIONS], key=key
        )
    elif step.key == "authorization":
        authorized = st.radio(
            "Are you legally authorized to work in the country where you're searching?",
            YES_NO_LATER, index=YES_NO_LATER.index(bool_to_answer(goals.get("authorized_to_work"))),
            key="wiz_authorized", horizontal=True,
        )
        sponsorship = st.radio(
            "Will you now or in the future need an employer to sponsor a work visa?",
            YES_NO_LATER, index=YES_NO_LATER.index(bool_to_answer(goals.get("sponsorship_required"))),
            key="wiz_sponsorship", horizontal=True,
        )
        goals["authorized_to_work"] = answer_to_bool(authorized)
        goals["sponsorship_required"] = answer_to_bool(sponsorship)

    last = step_no == len(WIZARD_STEPS) - 1
    back, skip, go = st.columns([1, 1, 2])
    if back.button("Back", disabled=step_no == 0, key="wiz_back", use_container_width=True):
        st.session_state[WIZARD_STEP_KEY] = step_no - 1
        st.rerun()
    if not step.required and not last and skip.button("Skip", key="wiz_skip", use_container_width=True):
        st.session_state[WIZARD_STEP_KEY] = step_no + 1
        st.rerun()
    if go.button(on_done_label if last else "Continue", type="primary", disabled=not step_valid(step, goals),
                 key="wiz_continue", use_container_width=True):
        if last:
            save_goals(record, goals)
            save_record(st.session_state, owner_id, record)
            st.session_state.pop(WIZARD_DRAFT_KEY, None)
            st.session_state[WIZARD_STEP_KEY] = 0
            st.toast("Goals saved.")
            return True
        st.session_state[WIZARD_STEP_KEY] = step_no + 1
        st.rerun()
    return False
