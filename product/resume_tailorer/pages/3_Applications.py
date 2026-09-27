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

from resume_tailorer.applications.models import ApplicationMode, ApplicationStatus
from resume_tailorer.applications.status_tracker import StatusTracker
from resume_tailorer.applications.ui_helpers import format_application_for_display
from resume_tailorer.job_search.job_service import JobService, PENDING_TAILOR_JOB_KEY

# Session-state key used to look up the user's CareerTruthProfile, if one has
# been built elsewhere in the app (e.g. via the resume tailorer flow).
CAREER_PROFILE_SESSION_KEY = "career_profile"

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
    st.warning(
        "⚠️ Assist and Auto modes attempt a real submission to the employer's ATS only when you "
        "click Confirm & Submit below — nothing is ever submitted automatically. That said: "
        "verified live against a real Greenhouse posting, Assist/Auto mode does not currently "
        "work — real application forms are rendered by JavaScript, and almost none of their "
        "fields exist in the plain HTML this tool reads (see decisions/012 for the full finding). "
        "It also does not yet attach your resume PDF to a real submission. **Manual mode is the "
        "only mode that reliably works today** — it gives you the application link to complete "
        "yourself and tracks it on the dashboard below. Preview (dry run) is always safe and "
        "never contacts the real form, and will honestly report when a posting's form can't be "
        "read automatically."
    )


def _render_submit_tab(service: JobService) -> None:
    """Render the application submission form and handle Preview/Confirm & Submit."""
    st.subheader("Submit an Application")

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

    resume_pdf_path = st.text_input(
        "Tailored resume PDF path",
        value=st.session_state.get("last_pdf_path", ""),
        help="Path to the tailored resume PDF you generated for this job on the main page.",
        key="apply_resume_pdf_path",
    )
    stored_match = st.session_state.get("last_resume_match_score")
    default_match = float(stored_match) * 100 if isinstance(stored_match, float) and stored_match <= 1 else float(stored_match or 0.0)
    resume_match_score = st.number_input(
        "Resume Match score for this job (from the main page's report)",
        min_value=0.0,
        max_value=100.0,
        value=min(default_match, 100.0),
        key="apply_resume_match_score",
    )
    st.caption(
        "Pre-filled from the last tailoring run when available. 0 means unknown, not a real 0% match."
    )

    preview_clicked = st.button("Preview (dry run — never submits)")
    confirm_understanding = st.checkbox(
        "I understand this may attempt a real submission to the employer's ATS."
    )
    preview_done = bool(st.session_state.get("apply_preview_done"))
    submit_clicked = st.button(
        "Confirm & Submit (real submission for Assist/Auto)",
        disabled=not (confirm_understanding and preview_done),
    )
    if not preview_done:
        st.caption("Run Preview first. Confirm & Submit stays disabled until a preview succeeds.")

    profile = st.session_state.get(CAREER_PROFILE_SESSION_KEY)

    if (preview_clicked or submit_clicked) and not profile:
        st.error("No resume profile found. Upload and parse a resume on the main page first.")
    elif (preview_clicked or submit_clicked) and not job_id_input:
        st.error("Job ID is required.")
    elif preview_clicked or submit_clicked:
        dry_run = not submit_clicked
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
                st.session_state["apply_preview_done"] = True
                st.success(f"Preview generated. Application ID: {result.application_id}")
            else:
                st.success(
                    f"Application submitted. Application ID: {result.application_id}"
                    + (f", Confirmation: {result.confirmation_number}" if result.confirmation_number else "")
                )
            st.write(f"**Application link:** {result.form_url}")
            st.write("**Fields that would be / were submitted:**")
            st.json(result.form_fields_submitted)
        except ValueError as exc:
            if "Unknown ATS platform" in str(exc) or "not supported" in str(exc):
                st.error(
                    "This job wasn't sourced from a supported ATS (Greenhouse, Lever, or Ashby), "
                    "so it can't be auto-filled or auto-submitted here. Apply directly on the "
                    "job's own site instead."
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
    """Render the application status dashboard: filter, list, view history, update status."""
    st.subheader("Application Status Dashboard")

    # Go through StatusTracker rather than ApplicationDatabase directly: it is the
    # narrow status-only interface built for exactly this caller, and it is a
    # cheap stateless wrapper, so constructing it per render is fine.
    status_tracker = StatusTracker(service.applications_db)

    status_filter_ui = st.selectbox(
        "Filter by status",
        options=["All"] + list(STATUS_BY_LABEL.keys()),
        key="dashboard_status_filter",
    )

    if status_filter_ui == "All":
        applications = status_tracker.get_all_applications()
    else:
        applications = status_tracker.get_applications_by_status(
            STATUS_BY_LABEL[status_filter_ui]
        )

    if not applications:
        st.info("No applications found for this filter.")
        return

    rows = [format_application_for_display(a) for a in applications]
    st.dataframe(rows, use_container_width=True)

    st.subheader("Update Status / View History")
    selected_app_id = st.selectbox(
        "Select an application",
        options=[a.application_id for a in applications],
        key="dashboard_selected_app",
    )
    if not selected_app_id:
        return

    history = status_tracker.get_status_history(selected_app_id)
    st.write("**Status history:**")
    for h in history:
        st.write(
            f"- {h.status_updated.strftime('%Y-%m-%d %H:%M')} — {STATUS_LABELS[h.status]}"
            + (f" ({h.notes})" if h.notes else "")
        )

    new_status_ui = st.selectbox(
        "Update to status",
        options=list(STATUS_BY_LABEL.keys()),
        key="new_status_select",
    )
    update_notes = st.text_input("Notes (optional)", key="update_notes")
    if st.button("Update Status"):
        status_tracker.update_status(
            selected_app_id, STATUS_BY_LABEL[new_status_ui], update_notes
        )
        st.success("Status updated.")
        st.rerun()


def main():
    st.title("Applications")
    _render_disclosure_banner()

    service = _get_job_service()

    tab_submit, tab_dashboard = st.tabs(["Submit Application", "Status Dashboard"])
    with tab_submit:
        _render_submit_tab(service)
    with tab_dashboard:
        _render_dashboard_tab(service)


if __name__ == "__main__":
    main()
