"""
Streamlit Applications page (Sprint 3, Task 7).

Lets the user submit a job application (Manual/Assist/Auto mode, with a
safe dry-run Preview always available) and track every application's
status through the hiring funnel on a dashboard.

All non-trivial logic (formatting an ApplicationTracker for table display)
lives in `resume_tailorer.applications.ui_helpers`, which contains no
Streamlit calls and is covered by tests in
tests/test_application_ui_helpers.py. This file is responsible only for
rendering and wiring up Streamlit widgets — it is not unit tested
directly, by design (Streamlit UI requires a browser to exercise
meaningfully), matching the pattern established in `2_Job_Search.py`.

Safety: nothing in this page ever submits a real application without the
user explicitly clicking "Confirm & Submit". Preview always passes
dry_run=True. See the warning banner below for the current, honest state
of the real-submission path.
"""

import streamlit as st

from resume_tailorer.session_profile import get_career_profile
from resume_tailorer.tailoring_session import handoff_for_job

from resume_tailorer.applications.capabilities import get_capability
from resume_tailorer.applications.streamlit_views import build_launchpad_state, preview_token
from resume_tailorer.applications.models import ApplicationMode, ApplicationStatus, StatusSource
from resume_tailorer.applications.status_tracker import StatusTracker
from resume_tailorer.applications.ui_helpers import (
    STATUS_GROUPS,
    filter_applications,
    format_application_for_display,
    sort_applications,
)
from resume_tailorer.job_search.job_service import JobService, PENDING_TAILOR_JOB_KEY
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header

# Session-state key used to look up the user's CareerTruthProfile, if one has
# been built elsewhere in the app (e.g. via the resume tailorer flow).

st.set_page_config(page_title="Applications", page_icon="\U0001F4E8", layout="wide")

DB_PATH = "job_search.db"
APPLICATIONS_DB_PATH = "applications.db"

MODE_OPTIONS = {
    "Manual (I'll apply myself)": ApplicationMode.MANUAL,
    "Assist (pre-fill, I review before submitting)": ApplicationMode.ASSIST,
    "Auto (auto-submit known fields)": ApplicationMode.AUTO,
}

STATUS_LABELS = {s: s.value.replace("_", " ").title() for s in ApplicationStatus}
STATUS_BY_LABEL = {label: status for status, label in STATUS_LABELS.items()}


def _get_job_service() -> JobService:
    """Get (or lazily create) the JobService instance stored in session state."""
    if "job_service" not in st.session_state:
        st.session_state.job_service = JobService(
            db_path=DB_PATH, applications_db_path=APPLICATIONS_DB_PATH
        )
    return st.session_state.job_service


def _render_disclosure_banner() -> None:
    st.info(
        "Manual mode is the reliable path today. Preview is always a dry run; Assist and Auto remain disabled for real submission unless a platform capability explicitly proves otherwise."
    )


def _render_submit_tab(service: JobService) -> None:
    """Render the application submission form and handle Preview/Confirm & Submit."""
    st.subheader("Stage this application")

    # Pre-filled from the Job Search page's "Apply" handoff when available
    # (same pending_tailor_job snapshot used to prefill the Resume Tailorer),
    # so the job ID doesn't have to be copy-pasted by hand.
    pending_job = st.session_state.get(PENDING_TAILOR_JOB_KEY) or {}
    job_id_input = st.text_input(
        "Job ID",
        value=pending_job.get("job_id", ""),
        help="The job ID from the Job Search dashboard (format: source_sourceid). "
        "Pre-filled automatically after clicking Apply on the Job Search page.",
        key="apply_job_id",
    )

    mode_choice_ui = st.selectbox(
        "Application Mode", options=list(MODE_OPTIONS.keys()), key="apply_mode"
    )
    mode = MODE_OPTIONS[mode_choice_ui]

    # Tailoring Studio hands over the validated artifact for this job; a newer
    # version replaces whatever was filled in for an older one.
    handoff = handoff_for_job(st.session_state, job_id_input)
    if handoff and st.session_state.get("apply_handoff_sha") != handoff["sha256"]:
        st.session_state["apply_handoff_sha"] = handoff["sha256"]
        st.session_state["apply_resume_pdf_path"] = handoff["pdf_path"]
        score = handoff.get("resume_match_score")
        st.session_state["apply_resume_match_score"] = (
            min(float(score) * 100, 100.0) if isinstance(score, (int, float)) else 0.0
        )
    resume_pdf_path = st.text_input(
        "Tailored resume PDF path",
        help="Filled in from Tailoring Studio when a validated resume exists for this job.",
        key="apply_resume_pdf_path",
    )
    resume_match_score = st.number_input(
        "Resume Match score for this job",
        min_value=0.0,
        max_value=100.0,
        key="apply_resume_match_score",
    )
    if handoff:
        st.caption(
            f"Using tailored resume version {handoff['version']} "
            f"(validation: {handoff['validation_status']})."
        )
    else:
        st.caption("No validated tailored resume for this job yet. 0 means unknown, not a real 0% match.")

    # Look up the platform's declared capability BEFORE rendering the submit
    # button, so a platform that can't complete a real submission (every
    # platform today -- decision 016) gets a hard-disabled button with a
    # clear reason, not just a checkbox + hope the engine's own safety gate
    # catches it after the click.
    job_lookup = service.db.get_job_posting(job_id_input) if job_id_input else None
    ats_platform = (job_lookup.ats_platform if job_lookup else "") or ""
    capability = get_capability(ats_platform)
    launchpad = build_launchpad_state(mode, capability)
    real_submit_possible = mode == ApplicationMode.MANUAL or capability.final_submission

    checklist = st.columns(3)
    checklist[0].metric("Job", "Ready" if job_lookup else "Missing")
    checklist[1].metric("Resume", "Ready" if resume_pdf_path else "Missing")
    checklist[2].metric("Profile", "Ready" if get_career_profile(st.session_state) else "Missing")
    st.markdown(f'<div class="jc-status review">{launchpad.disclosure}</div>', unsafe_allow_html=True)

    preview_clicked = st.button("Preview (dry run — never submits)")
    confirm_understanding = st.checkbox(
        "I reviewed the staged application and want to continue.",
        disabled=not real_submit_possible,
    )
    profile = get_career_profile(st.session_state)
    current_token = preview_token(job_id_input, resume_pdf_path, profile, mode)
    preview_done = st.session_state.get("apply_preview_token") == current_token
    if job_lookup and job_lookup.url:
        st.link_button(
            launchpad.primary_action,
            job_lookup.url,
            type="primary",
            use_container_width=True,
        )
    stage_clicked = st.button(
        launchpad.tracker_action,
        disabled=not (real_submit_possible and confirm_understanding and preview_done),
    )
    if mode != ApplicationMode.MANUAL and not capability.final_submission:
        st.info(
            f"Confirm & Submit is disabled for {ats_platform or 'this platform'} in "
            f"{mode.value.title()} mode: {capability.notes or 'real submission is not yet supported.'} "
            f"Use Preview to see what would be attempted, or switch to Manual mode to apply yourself."
        )
    if not preview_done:
        st.caption(
            "Run Preview first. Staying enabled requires the same job, resume, profile and mode you previewed."
        )

    if (preview_clicked or stage_clicked) and not profile:
        st.error("No resume profile found. Upload and parse a resume on the main page first.")
    elif (preview_clicked or stage_clicked) and not job_id_input:
        st.error("Job ID is required.")
    elif preview_clicked or stage_clicked:
        dry_run = not stage_clicked
        try:
            result = service.apply_for_job(
                job_id=job_id_input,
                profile=profile,
                resume_pdf_path=resume_pdf_path,
                mode=mode,
                resume_match_score=resume_match_score,
                dry_run=dry_run,
            )
            if dry_run:
                st.session_state["apply_preview_token"] = current_token
                st.success("Preview ready. Nothing was saved; stage it when you're ready.")
            else:
                st.success(f"{launchpad.success_message} Application ID: {result.application_id}")
            st.write(f"**Application link:** {result.form_url}")
            st.write("**Fields that would be / were submitted:**")
            st.json(result.form_fields_submitted)
        except ValueError as exc:
            if "Unknown ATS platform" in str(exc) or "not supported" in str(exc):
                st.error(
                    "This job's application site can't be auto-filled here. Switch to "
                    "**Manual mode** to stage it and apply on the employer's site yourself."
                )
            elif "could not parse any application fields" in str(exc):
                # Found live (2026-09-27): real Greenhouse application forms are
                # rendered by client-side JavaScript with almost no named HTML
                # form elements in the raw page -- this isn't a rare edge case,
                # it's the normal shape of a real posting today. Tell the user
                # what's actually true instead of surfacing a generic parse error.
                st.error(
                    "This posting's application form could not be read automatically -- it's "
                    "likely rendered by JavaScript, which Assist/Auto mode can't see through "
                    "today. This is a known limitation (see decisions/012), not specific to this "
                    "job. Use **Manual mode** to get the application link and apply directly on "
                    "the employer's site."
                )
            else:
                st.error(f"Could not submit: {exc}")


def _render_dashboard_tab(service: JobService) -> None:
    """Render the application status dashboard: saved views, filters,
    sorting, application detail, next-action, and status history/update."""
    st.subheader("Application Status Dashboard")

    # Go through StatusTracker rather than ApplicationDatabase directly for
    # status operations: it is the narrow status-only interface built for
    # exactly this caller. Submission/snapshot data (Company/Role/Fit/
    # Resume version/Next action) comes from applications_db directly,
    # since StatusTracker deliberately doesn't expose that surface.
    status_tracker = StatusTracker(service.applications_db)
    trackers = status_tracker.get_all_applications()

    if not trackers:
        st.info("No applications yet. Submit one from the 'Submit Application' tab.")
        return

    # Pair each current-status tracker with its submission snapshot (may be
    # None only if the application row was somehow deleted independently --
    # format_application_for_display degrades gracefully in that case).
    submissions_by_id = {
        t.application_id: service.applications_db.get_submission(t.application_id) for t in trackers
    }
    rows = [format_application_for_display(t, submissions_by_id[t.application_id]) for t in trackers]

    view = st.radio("View", options=list(STATUS_GROUPS.keys()), horizontal=True, key="dashboard_view")

    filter_cols = st.columns(4)
    with filter_cols[0]:
        company_filter = st.text_input("Company", key="dashboard_filter_company")
    with filter_cols[1]:
        role_filter = st.text_input("Role", key="dashboard_filter_role")
    with filter_cols[2]:
        mode_filter = st.selectbox(
            "Mode", options=["", "Manual", "Assist", "Auto"], key="dashboard_filter_mode"
        )
    with filter_cols[3]:
        min_fit_filter = st.number_input(
            "Min Candidate Fit %", min_value=0.0, max_value=100.0, value=0.0, step=5.0,
            key="dashboard_filter_min_fit",
            help="0 shows all applications, including ones with no fit score recorded.",
        )

    sort_by = st.selectbox(
        "Sort by",
        options=["Newest application", "Oldest pending", "Company", "Status", "Candidate Fit"],
        key="dashboard_sort_by",
    )

    filtered = filter_applications(
        rows,
        view=view,
        company=company_filter,
        role=role_filter,
        mode=mode_filter,
        min_fit=min_fit_filter if min_fit_filter > 0 else None,
    )
    filtered = sort_applications(filtered, sort_by)

    if not filtered:
        st.info("No applications match the current view/filters.")
        return

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.subheader("Application Detail")
    id_to_company = {r["Application ID"]: f"{r['Company']} — {r['Role']}" for r in filtered}
    selected_app_id = st.selectbox(
        "Select an application",
        options=list(id_to_company.keys()),
        format_func=lambda app_id: id_to_company.get(app_id, app_id),
        key="dashboard_selected_app",
    )
    if not selected_app_id:
        return

    submission = submissions_by_id.get(selected_app_id)
    if submission:
        detail_cols = st.columns(2)
        with detail_cols[0]:
            st.write(f"**Company:** {submission.job_snapshot.get('company', '—')}")
            st.write(f"**Role:** {submission.job_snapshot.get('title', '—')}")
            st.write(f"**Application URL:** {submission.form_url or '—'}")
            st.write(f"**Mode:** {submission.mode.value.title()}")
            st.write(f"**Resume used:** {submission.resume_used or '—'}")
        with detail_cols[1]:
            fit = submission.candidate_fit_snapshot.get("overall_fit")
            st.write(f"**Candidate Fit at submission:** {f'{fit:.0f}%' if fit is not None else '—'}")
            st.write(f"**Confirmation:** {submission.confirmation_number or '—'}")
            st.write(f"**Submitted:** {submission.submission_timestamp.strftime('%Y-%m-%d %H:%M')}")
        if submission.form_fields_submitted:
            with st.expander("Fields submitted"):
                st.json(submission.form_fields_submitted)

        st.write("**Next action:**")
        next_action_cols = st.columns([2, 1, 3])
        with next_action_cols[0]:
            next_action_input = st.text_input(
                "Action", value=submission.next_action, key="next_action_input", label_visibility="collapsed",
                placeholder="e.g. Prepare for interview",
            )
        with next_action_cols[1]:
            next_action_due_input = st.text_input(
                "Due (YYYY-MM-DD, optional)", value=submission.next_action_due or "",
                key="next_action_due_input", label_visibility="collapsed", placeholder="Due date",
            )
        with next_action_cols[2]:
            next_action_notes_input = st.text_input(
                "Notes", value=submission.next_action_notes, key="next_action_notes_input",
                label_visibility="collapsed", placeholder="Notes (optional)",
            )
        if st.button("Save next action"):
            service.applications_db.update_next_action(
                selected_app_id, next_action_input,
                next_action_due_input or None, next_action_notes_input,
            )
            st.success("Next action saved.")
            st.rerun()

    history = status_tracker.get_status_history(selected_app_id)
    st.write("**Status history:**")
    for h in history:
        provenance = f" [{h.source.value}" + (f", {h.confidence} confidence" if h.confidence else "") + "]"
        st.write(
            f"- {h.status_updated.strftime('%Y-%m-%d %H:%M')} — {STATUS_LABELS[h.status]}"
            + (f" ({h.notes})" if h.notes else "")
            + (provenance if h.source != StatusSource.USER else "")
        )

    new_status_ui = st.selectbox(
        "Update to status",
        options=list(STATUS_BY_LABEL.keys()),
        key="new_status_select",
    )
    update_notes = st.text_input("Notes (optional)", key="update_notes")
    if st.button("Update Status"):
        # Always source=USER from this control: a manual dashboard edit IS
        # the user's own correction, and must always be allowed regardless
        # of any prior automated entry (spec 003 Step 23).
        status_tracker.update_status(
            selected_app_id, STATUS_BY_LABEL[new_status_ui], update_notes, source=StatusSource.USER,
        )
        st.success("Status updated.")
        st.rerun()


def main():
    render_app_shell("Apply Launchpad", build_workflow_state(st.session_state))
    render_page_header(
        "Apply Launchpad",
        "Stage the verified job link, tailored resume, and reusable facts before you finish on the employer site.",
    )
    _render_disclosure_banner()

    service = _get_job_service()
    _render_submit_tab(service)


if __name__ == "__main__":
    main()
