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
from resume_tailorer.applications.models import ApplicationMode
from resume_tailorer.job_search.job_service import JobService, PENDING_TAILOR_JOB_KEY
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header

st.set_page_config(page_title="Applications", page_icon="\U0001F4E8", layout="wide")

DB_PATH = "job_search.db"
APPLICATIONS_DB_PATH = "applications.db"

MODE_OPTIONS = {
    "Manual (I'll apply myself)": ApplicationMode.MANUAL,
    "Assist (pre-fill, I review before submitting)": ApplicationMode.ASSIST,
    "Auto (auto-submit known fields)": ApplicationMode.AUTO,
}


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
