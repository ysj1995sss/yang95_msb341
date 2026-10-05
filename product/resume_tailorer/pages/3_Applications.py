"""Apply: readiness and an honest handoff to the employer's site (spec 007).

Manual mode is the default and the reliable path: it needs only a valid
employer link and never parses the application form (decision 021). Assist
and Auto stay unavailable until a platform proves real submission (decisions
012, 016; spec 006). Opening the employer page is never called submitting;
the user marks an application as applied themselves.

The job and the tailored resume arrive through the existing handoffs
(PENDING_TAILOR_JOB_KEY and tailoring_session); nothing is typed by hand.
Preview (a dry run) never creates an application record.
"""

import os
from html import escape

import streamlit as st

from resume_tailorer.applications.answer_bank import question_key
from resume_tailorer.applications.capabilities import get_capability
from resume_tailorer.applications.models import ApplicationMode, ApplicationStatus, StatusSource
from resume_tailorer.applications.status_tracker import StatusTracker
from resume_tailorer.applications.streamlit_views import preview_token
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY, JobService
from resume_tailorer.profile_import import RECORD_KEY
from resume_tailorer.session_profile import get_career_profile
from resume_tailorer.tailoring_session import handoff_for_job
from resume_tailorer.ui import chip, render_app_shell, render_page_header, render_progress
from resume_tailorer.ui.apply_readiness import build_apply_view, empty_apply_view
from resume_tailorer.ui.shell import primary_action
from resume_tailorer.ui.auth_gate import OWNER_KEY, job_service_for, require_identity
from resume_tailorer.ui.design_system import ProgressStep
from resume_tailorer.ui.profile_readiness import build_readiness
from resume_tailorer.ui.tailor_progress import review_progress
from resume_tailorer.ui.tailoring_view import group_changes
from resume_tailorer.ui.artifact_review import visible_changes

st.set_page_config(page_title="Apply · Job Copilot", page_icon="\U0001F4E8", layout="wide")

_STATE_ICONS = {"ok": ("✓", "verified"), "review": ("!", "review"), "blocked": ("✕", "blocked"), "neutral": ("–", "")}


def _service() -> JobService:
    return job_service_for(st.session_state[OWNER_KEY])


def _current_application(service: JobService, job_id: str):
    """The latest application record for this job and its status, or (None, None)."""
    subs = service.applications_db.get_submissions_by_job(job_id) if job_id else []
    if not subs:
        return None, None
    latest = sorted(subs, key=lambda s: s.submission_timestamp)[-1]
    return latest, service.applications_db.get_current_status(latest.application_id)


def _review_complete() -> bool:
    state = st.session_state.get("artifact_run_state")
    if not state:
        handoff = st.session_state.get("tailored_artifact_handoff") or {}
        return bool(handoff.get("review_complete"))
    report = state["report"]
    reviewable = group_changes(visible_changes(state["changes"]), report.true_gaps).reviewable
    progress = review_progress(reviewable, state.get("decided", set()), state.get("dirty", False), report.validation.status)
    return progress.can_continue


def _pick_staged(service: JobService) -> None:
    """No active job: offer staged applications waiting to be finished."""
    tracker = StatusTracker(service.applications_db)
    staged = [t for t in tracker.get_all_applications() if t.status == ApplicationStatus.READY_TO_APPLY]
    view = empty_apply_view(False, False)
    main, side = st.columns([2, 1], gap="large")
    with main:
        with st.container(border=True):
            st.markdown('<h2 class="jc-card-title">To prepare an application</h2>'
                        '<p class="jc-meta">Apply checks that everything is ready, then sends you to the '
                        "employer's own application. It never submits for you.</p>", unsafe_allow_html=True)
            st.markdown("".join(
                f'<div class="jc-check"><span>{i}. {label}</span>{chip("Done" if done else "Not yet", "verified" if done else "")}</div>'
                for i, (label, done) in enumerate(view.items, start=1)), unsafe_allow_html=True)
            primary_action(view.action_label, view.action_page, "apply_empty_next")
    with side:
        st.markdown('<div class="jc-aside"><h3>Why Manual mode</h3><p>Most application forms are built in the '
                    "browser, so Job Copilot can't fill them reliably yet. You finish on the employer's site with "
                    "your tailored resume, then mark it as applied.</p></div>", unsafe_allow_html=True)
    if staged:
        st.markdown("### Or finish one you've already staged")
        for t in staged:
            sub = service.applications_db.get_submission(t.application_id)
            job = (sub.job_snapshot or {}) if sub else {}
            label = f"{job.get('title', 'Role')} at {job.get('company', '')}"
            if st.button(label, key=f"pick_{t.application_id}"):
                st.session_state[PENDING_TAILOR_JOB_KEY] = {
                    "job_id": t.job_posting_id, "title": job.get("title", ""), "company": job.get("company", ""),
                    "url": job.get("url", ""), "description": "", "candidate_fit": sub.candidate_fit_snapshot or {},
                }
                st.rerun()


def _render_checklist(view) -> None:
    rows = []
    for item in view.checklist:
        mark, tone = _STATE_ICONS[item.state]
        rows.append(
            f"<tr><td style='width:2.2rem'>{chip(mark, tone)}</td><th>{escape(item.label)}</th>"
            f"<td>{escape(item.detail)}</td></tr>"
        )
    st.markdown(f'<table class="jc-table" aria-label="Readiness checklist">{"".join(rows)}</table>', unsafe_allow_html=True)


def _render_modes(view) -> None:
    st.markdown("### How you'll apply")
    for mode in view.modes:
        if mode.available:
            tag = chip("Recommended" if mode.recommended else "Available", "verified")
        else:
            tag = chip("Not offered" if mode.name == "Auto" else "Not available yet")
        st.markdown(
            f'<div class="jc-row"><strong>{"● " if mode.name == "Manual" else "○ "}{escape(mode.name)}</strong> {tag}<br>'
            f'<span class="jc-meta">{escape(mode.detail)}</span></div>',
            unsafe_allow_html=True,
        )


def _render_kit(record: dict, handoff, answers: list) -> None:
    """Assist: the answers the employer's form asks for, ready to copy (decision 027)."""
    from resume_tailorer.ui.application_kit import MISSING, OPTIONAL, READY, build_kit, helper_payload, kit_summary

    fields = build_kit(record, handoff, answers)
    st.markdown("### Assist: your application kit")
    st.caption("Open the employer's form beside this, then copy each answer across. "
               "Everything here comes from your confirmed profile, your tailored resume and answers you approved. "
               + kit_summary(fields))
    with st.container(border=True, key="apply_kit"):
        for field in fields:
            if field.state == OPTIONAL:
                continue
            label, value = st.columns([2, 3], vertical_alignment="center")
            label.markdown(f"**{escape(field.label)}**  \n<span class='jc-meta'>{escape(field.source)}</span>",
                           unsafe_allow_html=True)
            if field.state == READY and field.label == "Resume":
                value.markdown(f"{escape(field.value)} · use the download above", unsafe_allow_html=True)
            elif field.state == READY:
                value.code(field.value, language=None, wrap_lines=True)
            elif field.state == MISSING:
                value.markdown(f"{chip('Missing', 'review')} Add it in {escape(field.fix)}", unsafe_allow_html=True)
    optional = [f.label for f in fields if f.state == OPTIONAL]
    if optional:
        st.caption("Not in your profile (often optional): " + ", ".join(optional) + ".")
    with st.expander("Fill the form for me with the browser helper"):
        st.markdown(
            "1. Install the Job Copilot form helper in Chrome or Edge (the repo's `extension` folder; "
            "its README has the steps).\n"
            "2. Copy the helper code below and paste it into the helper once. It stays in your browser only.\n"
            "3. Open the employer's application and click **Fill this page**. Green fields were filled from your "
            "kit; amber ones are left for you. Attach your resume, check everything, then submit yourself."
        )
        st.code(helper_payload(fields), language="json", wrap_lines=True)


def _render_questions(service: JobService, job_id: str, profile, handoff) -> None:
    with st.expander("Check the form for custom questions"):
        st.caption("Optional. Tries to read the employer's form so you can answer questions here once and reuse them. "
                   "Nothing is submitted or saved by checking.")
        if st.button("Check for questions", key="apply_check_questions"):
            try:
                result = service.apply_for_job(
                    job_id=job_id, profile=profile, resume_pdf_path=(handoff or {}).get("pdf_path", ""),
                    mode=ApplicationMode.ASSIST, resume_match_score=0.0, dry_run=True,
                )
                st.session_state["apply_unanswered"] = list(result.unanswered_questions)
                st.session_state["apply_answers_used"] = dict(result.custom_answers or {})
                if not result.unanswered_questions:
                    st.success("No unanswered questions were found on the form.")
            except ValueError:
                st.info("This employer's form can't be read automatically (most are built in the browser). "
                        "You'll see any extra questions on their site.")
        used = st.session_state.get("apply_answers_used") or {}
        if used:
            st.markdown("**Saved answers that match this form**")
            for question, answer in used.items():
                st.markdown(f"- {escape(question)}: {escape(answer)}")
        unanswered = list(dict.fromkeys(st.session_state.get("apply_unanswered") or []))
        if unanswered:
            st.markdown("**Questions that need your answer**")
            st.caption("Only answers you write here are saved and reused. Job Copilot never writes an answer for you.")
            typed = {q: st.text_area(q, key=f"answer_{i}_{question_key(q)}", height=70) for i, q in enumerate(unanswered)}
            if st.button("Approve and save answers"):
                saved = 0
                for q, a in typed.items():
                    if a.strip():
                        service.applications_db.save_answer(question_key(q), q, a.strip())
                        saved += 1
                st.session_state["apply_unanswered"] = [q for q, a in typed.items() if not a.strip()]
                st.toast(f"Saved {saved} {'answer' if saved == 1 else 'answers'}.")
                st.rerun()


def main():
    require_identity()
    render_app_shell("Apply")
    render_page_header(
        "Apply",
        "Check that everything is ready, then finish on the employer's own site. Job Copilot never submits for you.",
    )
    service = _service()
    job = st.session_state.get(PENDING_TAILOR_JOB_KEY) or {}
    if not job:
        _pick_staged(service)
        return

    job_id = job.get("job_id", "")
    handoff = handoff_for_job(st.session_state, job_id)
    if handoff and str(handoff.get("validation_status", "")).upper() == "FAIL":
        handoff = None  # a failed resume is never usable here
    stored = service.db.get_job_posting(job_id) if job_id else None
    if not job.get("url") and stored is not None:
        job = {**job, "url": stored.url}
    record = st.session_state.get(RECORD_KEY) or {}
    readiness = build_readiness(record)
    profile = get_career_profile(st.session_state)
    application, status = _current_application(service, job_id)
    capability = get_capability((stored.ats_platform if stored else "") or "")
    view = build_apply_view(
        job=job, handoff=handoff, review_complete=_review_complete(),
        facts_confirmed=readiness.facts_confirmed, has_profile=profile is not None,
        approved_answers=len(service.applications_db.get_answers()),
        unanswered=tuple(st.session_state.get("apply_unanswered") or ()),
        status=status, capability=capability,
    )

    render_progress(
        (
            ProgressStep("Resume ready", "complete" if handoff else "current"),
            ProgressStep("Tracked", "complete" if view.stage in ("tracked", "applied") else ("current" if handoff else "pending")),
            ProgressStep("Marked as applied", "complete" if view.stage == "applied" else ("current" if view.stage == "tracked" else "pending")),
        ),
        "Application readiness",
    )

    main_col, side = st.columns([2, 1], gap="large")
    with main_col:
        tone = {"ready": "verified", "tracked": "verified", "applied": "verified"}.get(view.stage, "review")
        st.markdown(
            f'<div class="jc-panel"><div class="jc-eyebrow">{escape(job.get("company", ""))}</div>'
            f'<h2 style="margin:.1rem 0 .4rem">{escape(job.get("title", "Role"))}</h2>'
            f'<div class="jc-status {tone}">{escape(view.headline)}</div></div>',
            unsafe_allow_html=True,
        )
        st.write("")
        _render_checklist(view)
        st.write("")
        a, b, c = st.columns(3)
        if view.can_open:
            a.link_button("Open employer application", job["url"], type="primary", use_container_width=True)
        else:
            a.button("Open employer application", disabled=True, use_container_width=True)
        if b.button("Track this application", disabled=not view.can_track, use_container_width=True,
                    help="Adds it to Tracker as ready to apply. Doesn't submit anything."):
            token_now = preview_token(job_id, handoff["pdf_path"], profile, ApplicationMode.MANUAL,
                                      service.applications_db.get_answers())
            try:
                # The dry run is the preview: nothing is saved by it.
                service.apply_for_job(job_id=job_id, profile=profile, resume_pdf_path=handoff["pdf_path"],
                                      mode=ApplicationMode.MANUAL,
                                      resume_match_score=_score(handoff), dry_run=True)
                st.session_state["apply_preview_token"] = token_now
                service.apply_for_job(job_id=job_id, profile=profile, resume_pdf_path=handoff["pdf_path"],
                                      mode=ApplicationMode.MANUAL,
                                      resume_match_score=_score(handoff), dry_run=False)
                st.toast("Tracked as ready to apply.")
                st.rerun()
            except ValueError as exc:
                st.error(f"Couldn't track this application: {exc}")
        if c.button("Mark as applied", disabled=not view.can_mark_applied, use_container_width=True,
                    help="Use this after you've submitted on the employer's site."):
            StatusTracker(service.applications_db).update_status(
                application.application_id, ApplicationStatus.APPLIED,
                "Marked as applied by you after finishing on the employer's site.", source=StatusSource.USER,
            )
            st.toast("Marked as applied.")
            st.rerun()
        if view.stage == "applied":
            st.page_link("pages/4_Application_Tracker.py", label="Open Tracker →")
        elif view.stage == "tracked":
            st.caption("Opening the employer's page doesn't submit anything. Mark it as applied once you've finished there.")
        if not handoff:
            st.page_link("pages/5_Tailor.py", label="Tailor your resume for this job →")
        if handoff and os.path.exists(handoff["pdf_path"]):
            with open(handoff["pdf_path"], "rb") as f:
                st.download_button("Download the tailored resume to attach", f.read(),
                                   file_name=f"tailored_resume_v{handoff['version']}.pdf", mime="application/pdf")
        _render_kit(record, handoff, service.applications_db.get_answer_entries())
        _render_questions(service, job_id, profile, handoff)
    with side:
        _render_modes(view)
        st.markdown("### Saved answers")
        st.caption("Answers you've approved for application questions live in your Career Profile.")
        st.page_link("pages/1_Profile_Review.py", label="Manage saved answers")


def _score(handoff) -> float:
    score = (handoff or {}).get("resume_match_score")
    return min(float(score) * 100, 100.0) if isinstance(score, (int, float)) else 0.0


main()
