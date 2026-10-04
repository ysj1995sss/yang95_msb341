"""Presentation helpers for Apply Launchpad and Application Tracker."""

from __future__ import annotations

from dataclasses import dataclass

from resume_tailorer.applications.models import (
    ATSCapability,
    ApplicationMode,
    ApplicationStatus,
    StatusSource,
)
from resume_tailorer.applications.status_tracker import StatusTracker
from resume_tailorer.applications.ui_helpers import (
    STATUS_GROUPS,
    filter_applications,
    format_application_for_display,
    sort_applications,
)


@dataclass(frozen=True)
class LaunchpadState:
    recommended_mode: ApplicationMode
    real_submit_enabled: bool
    primary_action: str
    tracker_action: str
    success_message: str
    disclosure: str


def build_launchpad_state(mode: ApplicationMode, capability: ATSCapability) -> LaunchpadState:
    automated_ready = mode is not ApplicationMode.MANUAL and capability.final_submission
    return LaunchpadState(
        recommended_mode=(mode if automated_ready else ApplicationMode.MANUAL),
        real_submit_enabled=automated_ready,
        primary_action="Submit application" if automated_ready else "Open application",
        tracker_action="Submit application" if automated_ready else "Stage in tracker",
        success_message=(
            "Application submitted with verified confirmation."
            if automated_ready
            else "Application staged as Ready to apply."
        ),
        disclosure=(
            "Verified automated submission is available for this platform."
            if automated_ready
            else "Manual mode is the reliable path today. You review and submit on the employer site."
        ),
    )


def _render_weekly_gauge(trackers, submissions) -> None:
    import streamlit as st
    from datetime import date

    from resume_tailorer.applications.weekly import build_weekly_summary

    entries = [
        (t.status, submissions[t.application_id].submission_timestamp.date() if submissions.get(t.application_id) else None)
        for t in trackers
    ]
    week = build_weekly_summary(entries, date.today())
    goal = int(st.session_state.get("weekly_goal", 0))
    left, right = st.columns([2, 3])
    with left:
        st.markdown(f"**Week of {week.week_start:%b %d} – {week.week_end:%b %d}**")
        st.metric("Applied this week", week.applied, delta=f"goal {goal}" if goal else None, delta_color="off")
        if goal:
            st.progress(min(week.applied / goal, 1.0))
        st.number_input("Weekly goal (0 = none)", min_value=0, max_value=100, key="weekly_goal")
    with right:
        a, b = st.columns(2)
        a.metric("In interview stages", week.interviews)
        b.metric("Saved, not applied", week.saved)


def render_application_tracker(service) -> None:
    """Render the tracker from existing immutable submission snapshots."""
    import streamlit as st

    status_tracker = StatusTracker(service.applications_db)
    trackers = status_tracker.get_all_applications()
    if not trackers:
        st.info("No applications yet. Use Apply Launchpad to stage your first one.")
        return

    submissions = {
        tracker.application_id: service.applications_db.get_submission(tracker.application_id)
        for tracker in trackers
    }
    rows = [format_application_for_display(t, submissions[t.application_id]) for t in trackers]
    _render_weekly_gauge(trackers, submissions)
    view = st.radio("Saved view", list(STATUS_GROUPS), horizontal=True, key="tracker_view")
    filters = st.columns(4)
    company = filters[0].text_input("Company", key="tracker_company")
    role = filters[1].text_input("Role", key="tracker_role")
    mode = filters[2].selectbox("Mode", ["", "Manual", "Assist", "Auto"], key="tracker_mode")
    sort_by = filters[3].selectbox(
        "Sort by", ["Newest application", "Oldest pending", "Company", "Status", "Candidate Fit"], key="tracker_sort"
    )
    shown = sort_applications(
        filter_applications(rows, view=view, company=company, role=role, mode=mode), sort_by
    )
    if not shown:
        st.info("No applications match these filters.")
        return
    st.dataframe(shown, use_container_width=True, hide_index=True)

    labels = {row["Application ID"]: f"{row['Company']} · {row['Role']}" for row in shown}
    application_id = st.selectbox("Application detail", list(labels), format_func=labels.get)
    submission = submissions.get(application_id)
    tracker = next(t for t in trackers if t.application_id == application_id)
    if submission:
        left, right = st.columns(2)
        left.markdown(
            f"**Application evidence**  \nResume: {submission.resume_used or 'Not recorded'}  \n"
            f"Mode: {submission.mode.value.title()}  \nURL: {submission.form_url or 'Not recorded'}"
        )
        fit = submission.candidate_fit_snapshot.get("overall_fit")
        right.markdown(
            f"**Submission snapshot**  \nCandidate fit: {f'{fit:.0f}%' if fit is not None else 'Not assessed'}  \n"
            f"Status: {tracker.status.value.replace('_', ' ').title()}  \n"
            f"Confirmation: {submission.confirmation_number or 'Not recorded'}"
        )
        next_action = st.text_input("Next action", value=submission.next_action, key="tracker_next_action")
        due = st.text_input("Due date (YYYY-MM-DD, optional)", value=submission.next_action_due or "", key="tracker_due")
        next_action_notes = st.text_area(
            "Next-action notes", value=submission.next_action_notes, key="tracker_next_action_notes"
        )
        if st.button("Save next action"):
            service.applications_db.update_next_action(application_id, next_action, due or None, next_action_notes)
            st.success("Next action saved.")
            st.rerun()

    with st.expander("Status provenance and history", expanded=True):
        for event in status_tracker.get_status_history(application_id):
            provenance = event.source.value.replace("_", " ").title()
            confidence = f" · {event.confidence} confidence" if event.confidence else ""
            note = f" · {event.notes}" if event.notes else ""
            st.write(
                f"{event.status_updated:%Y-%m-%d %H:%M} · "
                f"{event.status.value.replace('_', ' ').title()} · {provenance}{confidence}{note}"
            )

    status_labels = {status.value.replace("_", " ").title(): status for status in ApplicationStatus}
    selected = st.selectbox("Update status", list(status_labels), key="tracker_status")
    notes = st.text_input("Status note (optional)", key="tracker_status_note")
    if st.button("Save status", type="primary"):
        status_tracker.update_status(application_id, status_labels[selected], notes, source=StatusSource.USER)
        st.success("Status saved with user provenance.")
        st.rerun()


def preview_token(
    job_id: str, resume_pdf_path: str, profile, mode: ApplicationMode, answers: dict | None = None
) -> str:
    """Identifies exactly what a preview approved: the job, the resume file's
    bytes, the profile version, the mode and the approved answers. Any change
    requires a new preview."""
    import hashlib
    import json
    import os

    from resume_tailorer.job_search.job_service import _profile_hash

    resume_id = resume_pdf_path or ""
    if resume_pdf_path and os.path.isfile(resume_pdf_path):
        with open(resume_pdf_path, "rb") as f:
            resume_id = hashlib.sha256(f.read()).hexdigest()
    parts = [job_id or "", resume_id, _profile_hash(profile) if profile else "", mode.value,
             sorted((answers or {}).items())]
    return hashlib.sha256(json.dumps(parts).encode("utf-8")).hexdigest()
