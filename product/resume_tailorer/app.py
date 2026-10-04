"""Home: the entry point (spec 007).

First-time users see a five-milestone journey with one dominant next action.
Returning users see a command center: the next best action, saved jobs,
drafts, applications ready to finish, follow-ups, weekly progress and recent
activity. All decisions about what to show live in ui/home_state.py.

Tailoring moved to pages/5_Tailor.py so Home can be the entry point.
"""

import sys
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

# Streamlit Community Cloud adds only this file's directory to sys.path; the
# app needs product/ (the parent of resume_tailorer/) to import its package.
_PRODUCT_DIR = str(Path(__file__).resolve().parent.parent)
if _PRODUCT_DIR not in sys.path:
    sys.path.insert(0, _PRODUCT_DIR)

from dotenv import load_dotenv
import streamlit as st

from resume_tailorer.llm.settings import apply_secret_settings

# Model settings come from a local .env, or from Streamlit secrets in the cloud.
load_dotenv()
try:
    apply_secret_settings(st.secrets)
except Exception:
    pass

from resume_tailorer.applications.models import ApplicationStatus
from resume_tailorer.applications.weekly import build_weekly_summary
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.profile_import import RECORD_KEY, import_resume, load_into_session, store_for
from resume_tailorer.tailoring_session import HANDOFF_KEY, handoff_for_job
from resume_tailorer.ui import render_app_shell
from resume_tailorer.ui.shell import primary_action
from resume_tailorer.ui.auth_gate import job_service_for, require_identity
from resume_tailorer.ui.goals_wizard import render_goals_wizard
from resume_tailorer.ui.home_state import (
    APPLY_PAGE,
    JOBS_PAGE,
    PROFILE_PAGE,
    TAILOR_PAGE,
    TRACKER_PAGE,
    HomeInputs,
    Item,
    build_home_view,
    due_items,
)
from resume_tailorer.ui.profile_readiness import build_readiness

st.set_page_config(page_title="Home · Job Copilot", page_icon="\U0001F9ED", layout="wide")

_CLOSED = {ApplicationStatus.OFFER, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}


def _gather(owner_id: str):
    record = st.session_state.get(RECORD_KEY) or {}
    readiness = build_readiness(record)
    service = job_service_for(owner_id)
    apps_db = service.applications_db
    trackers = apps_db.get_all_applications()
    submissions = {t.application_id: apps_db.get_submission(t.application_id) for t in trackers}

    pending = st.session_state.get(PENDING_TAILOR_JOB_KEY) or {}
    active = Item(pending["title"], pending.get("company", ""), TAILOR_PAGE) if pending.get("title") else None
    if active is None:
        earlier = service.db.get_jobs_by_latest_action("apply", limit=1)
        if earlier:
            active = Item(earlier[0].title, earlier[0].company, TAILOR_PAGE)
    state = st.session_state.get("artifact_run_state") or {}
    report = state.get("report")
    artifact_status = report.validation.status.value if report else None
    handoff = handoff_for_job(st.session_state, pending.get("job_id", "")) if pending else None

    saved = service.db.get_jobs_by_latest_action("save", limit=10)
    chosen = service.db.get_jobs_by_latest_action("apply", limit=1)

    from resume_tailorer.applications.status_tracker import StatusTracker
    from resume_tailorer.ui.tracker_views import build_row as tracker_row

    status_tracker = StatusTracker(apps_db)
    rows = [tracker_row(t, submissions.get(t.application_id), status_tracker.get_status_history(t.application_id))
            for t in trackers]
    ready = tuple(
        Item(f"{r.role} at {r.company}", "Tracked; finish on the employer's site", APPLY_PAGE)
        for r in rows if r.status == ApplicationStatus.READY_TO_APPLY
    )
    followup_rows = [
        {"title": r.role, "company": r.company, "next_action": r.next_action,
         "due": r.due.isoformat() if r.due else "", "closed": r.status in _CLOSED}
        for r in rows
    ]
    last_seen = service.db.latest_seen()
    week_start = date.today() - timedelta(days=date.today().weekday())
    inputs = HomeInputs(
        readiness=readiness,
        goals_set=bool((record.get("preferences") or {}).get("job_title")),
        role_chosen=bool(pending) or bool(chosen) or bool(trackers),
        application_prepared=bool(trackers),
        active_job=active,
        artifact_status=artifact_status,
        artifact_reviewed=bool(state.get("reviewed")) and not state.get("dirty"),
        handoff_ready=bool(handoff),
        saved_jobs=tuple(Item(f"{j.title} at {j.company}", j.location or "", JOBS_PAGE) for j in saved),
        ready_to_finish=ready,
        followups_due=due_items(followup_rows, date.today()),
        searched_this_week=bool(last_seen and last_seen.date() >= week_start),
    )
    recent_rows = [
        f"{r.last_update:%b %d} · {r.role} at {r.company}: {r.status.value.replace('_', ' ')}"
        for r in sorted(rows, key=lambda r: r.last_update, reverse=True)[:5]
    ]
    weekly_entries = [(r.status, r.applied) for r in rows]
    return record, inputs, build_weekly_summary(weekly_entries, date.today()), recent_rows


def _focus(action, eyebrow: str) -> None:
    st.markdown(
        f'<section class="jc-focus" aria-label="Your next best action"><div class="jc-eyebrow">{escape(eyebrow)}</div>'
        f"<h2>{escape(action.title)}</h2><p>{escape(action.why)}</p>"
        f'<p class="jc-value">{escape(action.value)}</p></section>',
        unsafe_allow_html=True,
    )


def identity_owner() -> str:
    from resume_tailorer.ui.auth_gate import OWNER_KEY

    return st.session_state[OWNER_KEY]


def _resume_chosen_job(owner_id: str, action):
    """When Home sends the user to Tailor or Apply without an active job, hand
    over the job they chose most recently, so nothing has to be picked again."""
    if action.page not in (TAILOR_PAGE, APPLY_PAGE) or st.session_state.get(PENDING_TAILOR_JOB_KEY):
        return None

    def load():
        from resume_tailorer.job_search.job_service import build_tailor_snapshot
        from resume_tailorer.session_profile import get_career_profile

        service = job_service_for(owner_id)
        earlier = service.db.get_jobs_by_latest_action("apply", limit=1)
        if earlier:
            profile = get_career_profile(st.session_state)
            fit = service.fit_scorer.score_fit_detailed(profile, earlier[0]) if profile else None
            st.session_state[PENDING_TAILOR_JOB_KEY] = build_tailor_snapshot(earlier[0], fit)

    return load


def _render_upload(owner_id: str) -> None:
    upload = st.file_uploader("Your resume (Word or PDF)", type=["docx", "pdf"], key="home_resume_upload")
    st.caption("Word (.docx) keeps your exact layout in tailored versions. Your file stays in your private folder.")
    if st.button("Import resume", type="primary", disabled=upload is None):
        try:
            with st.spinner("Reading your resume…"):
                import_resume(store_for(owner_id), upload.name, upload.getvalue())
                load_into_session(st.session_state, owner_id, force=True)
        except Exception as exc:
            st.error(f"We couldn't read that file: {exc}. Try the Word version, or a PDF with selectable text.")
            return
        st.toast("Resume imported.")
        st.rerun()


def _render_milestones(view) -> None:
    marks = {"complete": "✓", "current": "→", "pending": "○"}
    rows = "".join(
        f'<div class="jc-milestone {step.state}"><span class="jc-mark" aria-hidden="true">{marks[step.state]}</span>'
        f'<span>{index}. {escape(step.label)}<span class="jc-sr-only"> — {step.state}</span></span></div>'
        for index, step in enumerate(view.milestones, start=1)
    )
    st.markdown(f'<div class="jc-panel"><h3>Your setup</h3>{rows}</div>', unsafe_allow_html=True)


def _first_time(owner_id: str, view) -> None:
    st.markdown(
        '<header class="jc-page-header"><h1>Get your first application ready</h1>'
        "<p>Job Copilot finds real openings, shows why each one fits, and tailors your resume using only facts "
        "you've confirmed. You stay in control of every change and every application.</p></header>",
        unsafe_allow_html=True,
    )
    main, side = st.columns([2, 1], gap="large")
    action = view.next_action
    with main:
        _focus(action, f"Step {next((i for i, s in enumerate(view.milestones, 1) if s.state == 'current'), view.completed + 1)} of 5 · {view.completed} done")
        if action.inline == "upload":
            _render_upload(owner_id)
        elif action.inline == "goals":
            if render_goals_wizard(owner_id, "Save goals and continue"):
                st.rerun()
        else:
            primary_action(action.label, action.page, "home_next_action", before=_resume_chosen_job(identity_owner(), action))
    with side:
        _render_milestones(view)
        st.markdown(
            '<div class="jc-panel" style="margin-top:1rem"><h3>What Job Copilot won\'t do</h3>'
            "<p>Invent experience, guess legal answers, or submit an application for you.</p></div>",
            unsafe_allow_html=True,
        )


def _list_panel(title: str, items, empty: str) -> None:
    st.markdown(f"#### {escape(title)}")
    if not items:
        st.markdown(f'<p class="jc-meta">{escape(empty)}</p>', unsafe_allow_html=True)
        return
    for item in items[:5]:
        st.markdown(
            f'<div class="jc-row"><strong>{escape(item.title)}</strong><br><span class="jc-meta">{escape(item.detail)}</span></div>',
            unsafe_allow_html=True,
        )
    if len(items) > 5:
        st.caption(f"+{len(items) - 5} more")


def _returning(owner_id: str, view, record, weekly, recent) -> None:
    name = ((record.get("profile") or {}).get("contact_info") or {}).get("name", "")
    first = name.split()[0] if name else ""
    st.markdown(
        f'<header class="jc-page-header"><h1>{"Welcome back, " + escape(first) if first else "Welcome back"}</h1>'
        f"<p>{datetime.now():%A, %B %d}. Here's what needs you.</p></header>",
        unsafe_allow_html=True,
    )
    main, side = st.columns([2, 1], gap="large")
    action = view.next_action
    with main:
        _focus(action, "Your next best action")
        primary_action(action.label, action.page, "home_next_action", before=_resume_chosen_job(owner_id, action))
        st.write("")
        a, b = st.columns(2)
        with a:
            _list_panel("Follow-ups due", view.followups_due, "Nothing due. Add next actions in Tracker.")
            _list_panel("Ready to finish", view.ready_to_finish, "No staged applications waiting.")
        with b:
            _list_panel("Resumes awaiting your decisions", view.drafts, "No tailoring drafts open.")
            _list_panel("Saved jobs to review", view.saved_jobs, "No saved jobs. Save roles from Jobs to compare later.")
    with side:
        goal = int((record.get("preferences") or {}).get("weekly_goal") or 0)
        st.markdown("#### This week")
        st.metric("Applications sent", weekly.applied, help="Counted when you mark an application as applied.")
        if goal:
            st.progress(min(weekly.applied / goal, 1.0))
            st.caption(f"{weekly.applied} of your goal of {goal}. A steady pace beats a burst.")
        else:
            st.caption("Set a weekly goal in Tracker if it helps you pace yourself.")
        st.markdown("#### Quick actions")
        st.page_link(JOBS_PAGE, label="Find jobs", icon=":material/search:")
        st.page_link(TAILOR_PAGE, label="Tailor a resume", icon=":material/edit_document:")
        st.page_link(PROFILE_PAGE, label="Answer saved questions", icon=":material/quiz:")
        st.page_link(TRACKER_PAGE, label="Review applications", icon=":material/checklist:")
        st.markdown("#### Recent activity")
        if recent:
            for line in recent:
                st.markdown(f'<div class="jc-meta">{escape(line)}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="jc-meta">No activity yet.</div>', unsafe_allow_html=True)


def main():
    identity = require_identity()
    render_app_shell("Home")
    if st.session_state.get("profile_load_error"):
        st.error(
            "Your saved profile couldn't be read, so it isn't being used. "
            "Re-import your resume in Career Profile to rebuild it. "
            f"(Details: {st.session_state['profile_load_error']})"
        )
    try:
        record, inputs, weekly, recent = _gather(identity.owner_id)
    except Exception as exc:
        st.error(f"Some of your data couldn't be loaded: {exc}. Try reloading the page.")
        return
    view = build_home_view(inputs)
    if view.mode == "first_time":
        _first_time(identity.owner_id, view)
    else:
        _returning(identity.owner_id, view, record, weekly, recent)


main()
