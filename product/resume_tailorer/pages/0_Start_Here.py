"""Start Here: a guided checklist and a one-question-at-a-time goals wizard."""

from html import escape

import streamlit as st

from resume_tailorer.job_search.job_attributes import EXPERIENCE_LEVEL_OPTIONS, INDUSTRY_OPTIONS
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header
from resume_tailorer.ui.auth_gate import require_identity
from resume_tailorer.ui.onboarding import (
    BEFORE_AFTER,
    GOALS_KEY,
    HOW_IT_WORKS,
    START_PAGE,
    WIZARD_STEP_KEY,
    WIZARD_STEPS,
    WORK_MODES,
    build_checklist,
    goals_summary,
    next_item,
    progress,
    save_goals,
    step_valid,
)

st.set_page_config(page_title="Start Here", page_icon="🧭", layout="wide")

require_identity()
render_app_shell("Start Here", build_workflow_state(st.session_state))
render_page_header(
    "Start here",
    "Five steps from a resume to an application you can trust. We show what is done and what to do next.",
)

items = build_checklist(st.session_state)
done, total = progress(items)
upcoming = next_item(items)

def _story() -> None:
    cols = st.columns(len(HOW_IT_WORKS))
    for col, (num, title, body) in zip(cols, HOW_IT_WORKS):
        col.markdown(
            f'<div class="jc-panel"><strong>{num}. {escape(title)}</strong><p>{escape(body)}</p></div>',
            unsafe_allow_html=True,
        )
    rows = "".join(
        f"<tr><td>✗ {escape(b)}</td><td>✓ {escape(a)}</td></tr>" for b, a in BEFORE_AFTER
    )
    st.markdown(
        f'<table style="width:100%"><thead><tr><th>Without Job Copilot</th><th>With Job Copilot</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>",
        unsafe_allow_html=True,
    )


if done == 0:
    st.subheader("How it works")
    _story()
else:
    with st.expander("How it works"):
        _story()

head, cta = st.columns([3, 1])
with head:
    st.markdown(f"**{done} of {total} steps complete**")
    st.progress(done / total)
with cta:
    if upcoming and upcoming.page != START_PAGE:
        st.page_link(upcoming.page, label=f"Next: {upcoming.action} →", use_container_width=True)

for index, item in enumerate(items, start=1):
    mark = "✅" if item.done else ("👉" if item is upcoming else "⬜")
    left, right = st.columns([4, 1])
    with left:
        st.markdown(
            f"{mark} **{index}. {escape(item.label)}**  \n"
            f"<span style='color:#52606D'>{escape(item.detail)}</span>",
            unsafe_allow_html=True,
        )
    with right:
        if item.page != START_PAGE:
            st.page_link(item.page, label=item.action)

st.divider()
st.subheader("Your job goals")

goals = st.session_state.setdefault("_wizard_draft", dict(st.session_state.get(GOALS_KEY) or {}))
step_no = st.session_state.setdefault(WIZARD_STEP_KEY, 0)
editing = step_no < len(WIZARD_STEPS)

if st.session_state.get(GOALS_KEY) and not editing:
    for label, value in goals_summary(st.session_state[GOALS_KEY]):
        st.markdown(f"- **{label}:** {escape(value)}")
    c1, c2 = st.columns(2)
    if c1.button("Edit goals"):
        st.session_state[WIZARD_STEP_KEY] = 0
        st.rerun()
    c2.page_link("pages/2_Job_Search.py", label="Find jobs with these goals →")
else:
    step = WIZARD_STEPS[step_no]
    st.caption(f"Question {step_no + 1} of {len(WIZARD_STEPS)}")
    st.progress((step_no + 1) / len(WIZARD_STEPS))
    st.markdown(f"### {step.title}")
    st.caption(step.help)
    k = f"wiz_{step.key}"
    if step.key == "job_title":
        goals[step.key] = st.text_input("Job title", value=goals.get(step.key, ""), key=k, placeholder="e.g. Product Marketing Manager")
    elif step.key == "location":
        goals[step.key] = st.text_input("Location", value=goals.get(step.key, ""), key=k, placeholder="e.g. Salt Lake City, UT")
    elif step.key == "remote_preference":
        goals[step.key] = st.radio("Work mode", WORK_MODES, index=WORK_MODES.index(goals.get(step.key, "any")), key=k, horizontal=True)
    elif step.key == "experience_level":
        goals[step.key] = st.multiselect("Level", EXPERIENCE_LEVEL_OPTIONS, default=goals.get(step.key, []), key=k)
    elif step.key == "min_salary":
        goals[step.key] = st.slider("Minimum salary (USD)", 0, 300000, int(goals.get(step.key, 0)), step=5000, key=k)
    elif step.key == "sponsorship_required":
        goals[step.key] = st.radio("Need sponsorship?", ["No", "Yes"], index=1 if goals.get(step.key) else 0, key=k, horizontal=True) == "Yes"
    elif step.key == "industries":
        goals[step.key] = st.multiselect("Industries", INDUSTRY_OPTIONS, default=goals.get(step.key, []), key=k)

    back, skip, nxt = st.columns([1, 1, 2])
    if back.button("Back", disabled=step_no == 0):
        st.session_state[WIZARD_STEP_KEY] = step_no - 1
        st.rerun()
    if not step.required and skip.button("Skip"):
        goals.pop(step.key, None)
        st.session_state[WIZARD_STEP_KEY] = step_no + 1
        st.rerun()
    last = step_no == len(WIZARD_STEPS) - 1
    if nxt.button("Save goals" if last else "Continue", type="primary", disabled=not step_valid(step, goals)):
        if last:
            save_goals(st.session_state, goals)
        st.session_state[WIZARD_STEP_KEY] = step_no + 1
        st.rerun()
