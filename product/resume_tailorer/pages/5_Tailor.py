"""Tailor: the review room for one selected job (spec 007).

The tailoring pipeline is unchanged (spec 002, decisions 006/014/021/022): a
DOCX resume goes through the master-template splice pipeline, anything else
through the freeform path; both produce a validated artifact, a change list
and a final report. Review decisions are applied locally through
resume_tailorer.artifacts.regeneration, never by re-running the model.

The resume comes from the Career Profile (stored once, versioned). A one-off
file can still be used for a single job.
"""

import os
import sys
from html import escape
from pathlib import Path

_PRODUCT_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _PRODUCT_DIR not in sys.path:
    sys.path.insert(0, _PRODUCT_DIR)

from dotenv import load_dotenv
import streamlit as st

from resume_tailorer.llm.settings import apply_secret_settings

load_dotenv()
try:
    apply_secret_settings(st.secrets)
except Exception:
    pass

from resume_tailorer.identity import artifacts_dir
from resume_tailorer.profile_import import RECORD_KEY, store_for
from resume_tailorer.session_profile import get_career_profile
from resume_tailorer.ui.auth_gate import OWNER_KEY, job_service_for, require_identity
from resume_tailorer.ui.batch_panel import render_batch_switcher
from resume_tailorer.tailoring_session import HANDOFF_KEY, sync_pending_job
from resume_tailorer.llm.settings import resolve_settings
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.tailoring_service import TARGET_LENGTHS, TailoringError, regenerate, run_tailoring
from resume_tailorer.llm.ui import COMMON_MODELS, collect_sidebar_llm_fields
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.analyzers.term_match import displayable_gaps, short_requirement
from resume_tailorer.ui.shell import md_literal
from resume_tailorer.review_store import discard_review, load_review, save_review, signature
from resume_tailorer.artifacts.models import FidelityMode, ValidationStatus
from resume_tailorer.ui.artifact_review import visible_changes
from resume_tailorer.ui import ats_explainer, chip, render_app_shell, render_page_header, render_progress
from resume_tailorer.ui.ats_panel import (
    render_ats_explainer, render_keyword_report, render_readability, render_requirement_review,
)
from resume_tailorer.ui.requirement_review_view import (
    keyword_report_view, missing_list, readability_view, review_for_state, review_view,
)
from resume_tailorer.ui.shell import primary_action
from resume_tailorer.ui.design_system import ProgressStep
from resume_tailorer.ui.pdf_preview import pdf_page_images
from resume_tailorer.ui.tailor_progress import (
    DECISION_DONE,
    VERBS,
    artifact_status_text,
    artifact_tone,
    change_section_label,
    empty_queue_message,
    rejected_by_checks,
    next_undecided,
    readable_requirement,
    review_progress,
    supporting_fact,
    validation_word,
)
from resume_tailorer.ui.tailoring_view import group_changes, safe_default_dispositions


st.set_page_config(page_title="Tailor · Job Copilot", page_icon="\U0001F4C4", layout="wide")

_JD_SESSION_KEY = "job_description_text"
_STATE_KEY = "artifact_run_state"
_FOCUS_KEY = "tailor_focus_change"


def _percent(value) -> str:
    return f"{float(value):.0%}" if isinstance(value, (int, float)) else "Not assessed"


def _fit_label(pending: dict) -> str:
    overall = (pending.get("candidate_fit") or {}).get("overall_fit")
    return f"{round(overall)}%" if isinstance(overall, (int, float)) else "Not assessed"


_SAVED_SIGNATURE_KEY = "tailor_review_saved_signature"


def _save_review_if_changed(job_id) -> None:
    """Keep the review on disk so leaving mid-review loses no decisions."""
    state = st.session_state.get(_STATE_KEY)
    if not state or not job_id:
        return
    current = signature(state)
    if st.session_state.get(_SAVED_SIGNATURE_KEY) == (job_id, current):
        return
    if save_review(st.session_state.get("artifacts_dir"), job_id, state):
        st.session_state[_SAVED_SIGNATURE_KEY] = (job_id, current)


def _restore_review(job_id) -> None:
    if _STATE_KEY in st.session_state or not job_id or st.session_state.get("tailor_redo"):
        return
    restored = load_review(st.session_state.get("artifacts_dir"), job_id)
    if restored:
        st.session_state[_STATE_KEY] = restored
        st.session_state[_SAVED_SIGNATURE_KEY] = (job_id, signature(restored))


def _reset_review_state() -> None:
    st.session_state.pop(_STATE_KEY, None)
    st.session_state.pop(_FOCUS_KEY, None)


def _regenerate_from_current_dispositions() -> bool:
    """Apply the current per-change decisions and rebuild the artifact (tailoring_service).
    Returns False when a manual edit is rejected."""
    try:
        regenerate(st.session_state, st.session_state[_STATE_KEY])
    except TailoringError as exc:
        st.error(str(exc))
        return False
    return True


def _decide(change_id: str, choice: str) -> None:
    state = st.session_state[_STATE_KEY]
    if state["dispositions"].get(change_id) != choice or change_id not in state["decided"]:
        state["dirty"] = True
    state["dispositions"][change_id] = choice
    state["decided"].add(change_id)


def _render_context(pending: dict, state: dict | None) -> None:
    """Company, role, the two separate scores and the resume's status, always visible."""
    title = pending.get("title") or (state or {}).get("role") or "Your target role"
    company = pending.get("company") or (state or {}).get("company") or ""
    report = (state or {}).get("report")
    status = report.validation.status if report else None
    tone = artifact_tone(status)
    st.markdown(
        f'<div class="jc-panel"><div class="jc-eyebrow">{escape(company) or "Pasted job description"}</div>'
        f'<h2 style="margin:.1rem 0 .5rem">{escape(title)}</h2>'
        f'{chip("Candidate fit " + _fit_label(pending), "action")}'
        f'{chip(artifact_status_text(status), tone) if report else ""}'
        f'<p class="jc-meta" style="margin-top:.35rem">Candidate fit measures your background. '
        f"The review below shows how clearly this resume shows it, requirement by requirement.</p></div>",
        unsafe_allow_html=True,
    )
    render_ats_explainer()


def _render_change_focus(state: dict, change, profile) -> None:
    current = state["dispositions"].get(change.change_id)
    decided = change.change_id in state["decided"]
    with st.container(border=True):
        status_text = DECISION_DONE.get(current, "Not reviewed yet") if decided else "Not reviewed yet"
        st.markdown(
            f'<div class="jc-eyebrow">{escape(change_section_label(change))} · Review this change · {escape(status_text)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="jc-chain">'
            f'<div><small>Job requirement</small>{escape(readable_requirement(change))}</div><div class="jc-arrow">→</div>'
            f'<div><small>Supporting fact</small>{escape(supporting_fact(change, profile))}</div><div class="jc-arrow">→</div>'
            f'<div><small>Resume change</small>{escape(change.reason or "Reworded to match the posting")}</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Original**  \n{change.original_text or '(new line)'}")
        st.markdown(f"**Proposed**  \n{change.proposed_text}")
        st.markdown(
            f'<span class="jc-meta">Check: {escape(validation_word(change.validation_status))}</span>',
            unsafe_allow_html=True,
        )
        if current == "MANUALLY_EDITED" and decided:
            state["manual_texts"][change.change_id] = st.text_area(
                "Your wording",
                value=state["manual_texts"].get(change.change_id, change.proposed_text),
                key=f"manual_{change.change_id}",
                help="Only facts already in your Career Profile are allowed.",
            )
        cols = st.columns(3)
        for col, choice in zip(cols, ("ACCEPTED", "MANUALLY_EDITED", "REJECTED")):
            kind = "primary" if choice == "ACCEPTED" else "secondary"
            if col.button(VERBS[choice], key=f"decide_{choice}_{change.change_id}", type=kind, use_container_width=True):
                _decide(change.change_id, choice)
                if choice != "MANUALLY_EDITED":
                    st.session_state[_FOCUS_KEY] = next_undecided(
                        _reviewable(state), state["decided"], after=change.change_id
                    ) or change.change_id
                    st.toast(f"{DECISION_DONE[choice]}.")
                st.rerun()


def _reviewable(state: dict):
    shown = visible_changes(state["changes"], advanced=state.get("show_all", False))
    return group_changes(shown, state["report"].true_gaps).reviewable


def _render_review_room(pending: dict) -> None:
    state = st.session_state[_STATE_KEY]
    state.setdefault("decided", set())
    state.setdefault("dirty", False)
    report = state["report"]
    safe_defaults = safe_default_dispositions(state["changes"], report.true_gaps)
    if safe_defaults and not state.get("gap_blocks_applied"):
        state["dispositions"].update(safe_defaults)
        state["gap_blocks_applied"] = True
        _regenerate_from_current_dispositions()
        state["reviewed"] = False
        st.rerun()

    _render_context(pending, state)

    shown = visible_changes(state["changes"], advanced=state.get("show_all", False))
    groups = group_changes(shown, report.true_gaps)
    progress = review_progress(groups.reviewable, state["decided"], state["dirty"], report.validation.status)
    render_progress(
        (
            ProgressStep("Resume built", "complete"),
            ProgressStep(progress.label, "complete" if progress.reviewed == progress.total else "current"),
            ProgressStep(
                "Rebuilt with your decisions",
                "complete" if not progress.needs_rebuild and progress.reviewed == progress.total else
                ("current" if progress.reviewed == progress.total else "pending"),
            ),
            ProgressStep("Ready for Apply", "complete" if progress.can_continue else "pending"),
        ),
        "Review progress",
    )

    review, preview = st.columns([1.15, 0.85], gap="large")
    with review:
        st.markdown("### Proposed changes")
        if groups.reviewable:
            focus = st.session_state.get(_FOCUS_KEY)
            ids = [c.change_id for c in groups.reviewable]
            if focus not in ids:
                focus = next_undecided(groups.reviewable, state["decided"]) or ids[0]
            labels = {
                c.change_id: (
                    f"{'✓' if c.change_id in state['decided'] else '○'} "
                    f"{i}. {(c.job_requirement or c.original_text or 'Change')[:60]}"
                )
                for i, c in enumerate(groups.reviewable, start=1)
            }
            chosen = st.selectbox(
                "Review queue", ids, index=ids.index(focus), format_func=labels.get, key="tailor_queue"
            )
            st.session_state[_FOCUS_KEY] = chosen
            change = next(c for c in groups.reviewable if c.change_id == chosen)
            _render_change_focus(state, change, state["profile"])
        else:
            st.info(empty_queue_message(state["changes"]))

        turned_down = rejected_by_checks(state["changes"])
        if turned_down:
            with st.expander(f"Turned down by our checks ({len(turned_down)})"):
                st.caption("These proposals were not used. Your original wording stays.")
                for change in turned_down:
                    st.markdown(f"- **{escape(change.original_text[:90])}** — {escape(change.reason or 'did not pass the checks')}")

        state["show_all"] = st.checkbox(
            "Show unchanged and punctuation-only edits", value=state.get("show_all", False),
            help="Hidden by default because they don't change what your resume says.",
        )

        if state.get("sync_summary"):
            st.info(state["sync_summary"])
        review = review_for_state(state, (st.session_state.get(RECORD_KEY) or {}).get("provenance"))
        if review is not None:
            render_keyword_report(keyword_report_view(review, state))
            render_requirement_review(review_view(review))

        missing = missing_list(review) if review is not None else [
            {"label": short_requirement(g), "full": g} for g in displayable_gaps(groups.true_gaps)]
        if missing or groups.blocked:
            st.markdown("### Missing, never added")
            st.markdown(
                '<div class="jc-status blocked">These requirements aren\'t in your verified experience. '
                "Job Copilot will not add them.</div>",
                unsafe_allow_html=True,
            )
            for gap in missing:  # spec 011: from the requirement review, so every screen agrees
                st.markdown(f"- {md_literal(gap['label'])}", help=gap["full"] if gap["label"] != gap["full"] else None)
            for change in groups.blocked:
                st.markdown(
                    f"- Blocked a proposed line that claimed *{change.job_requirement or 'an unsupported requirement'}*; "
                    "the original was kept."
                )

    with preview:
        st.markdown('<span class="jc-sticky-marker"></span>', unsafe_allow_html=True)
        _render_preview(state)

    _render_action_bar(state, progress)
    _persist_handoff(progress.can_continue)


def _render_preview(state: dict) -> None:
    report = state["report"]
    status = report.validation.status
    st.markdown("### Resume preview")
    pages = f"{report.tailored_page_count} page(s)" if report.tailored_page_count else "Page count not checked"
    fidelity = "Original layout kept" if report.fidelity_mode is FidelityMode.PRESERVED else "Rebuilt layout; details may differ"
    st.markdown(
        f'{chip(artifact_status_text(status), artifact_tone(status))}{chip(pages)}'
        f'{chip("Version " + str(state.get("version", 1)))}{chip(fidelity)}',
        unsafe_allow_html=True,
    )
    if status is ValidationStatus.FAIL:
        st.error("This resume failed validation and can't be downloaded or used to apply.")
    elif status is ValidationStatus.WARNING:
        st.warning("Passed with warnings. Read them before you use this resume.")
    if status is not ValidationStatus.PASS:
        for finding in report.validation.findings:
            st.markdown(f"- {finding.message}")
    render_readability(readability_view(report.validation.findings, state.get("source_kind", ""),
                                        report.validation.checks_run))

    images = pdf_page_images(state.get("pdf_bytes") or b"")
    if images and status is not ValidationStatus.FAIL:
        for number, image in enumerate(images, start=1):
            st.image(image, caption=f"Page {number}", use_container_width=True)
    else:
        st.text_area("Resume text", state["tailored_text"], height=420, disabled=True)

    if status is not ValidationStatus.FAIL:
        name = state.get("candidate_name", "resume").replace(" ", "_")
        cols = st.columns(2)
        if state.get("pdf_bytes"):
            cols[0].download_button(
                "Download PDF", data=state["pdf_bytes"],
                file_name=f"{name}_tailored_resume.pdf", mime="application/pdf", use_container_width=True,
            )
        if state.get("docx_bytes"):
            cols[1].download_button(
                "Download Word", data=state["docx_bytes"],
                file_name=f"{name}_tailored_resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
    with st.expander("Details"):
        st.write(f"Pages: {report.original_page_count} before, {report.tailored_page_count} after.")
        st.write(f"Keyword overlap: {_percent(report.original_alignment)} before, {_percent(report.tailored_alignment)} after.")
        st.caption(ats_explainer.OVERLAP_NOTE)
        if report.unsupported_claims:
            st.write("Unsupported claims found and blocked:")
            for claim in report.unsupported_claims:
                st.write(f"- {claim}")
        for finding in report.validation.findings:
            st.write(f"- {finding.message}")


def _persist_handoff(review_complete: bool) -> None:
    """Keep the validated resume with the Career Profile so Apply finds it in a new session."""
    from resume_tailorer.active_job import remember_handoff
    from resume_tailorer.profile_import import save_record
    from resume_tailorer.ui.auth_gate import OWNER_KEY

    record = st.session_state.get(RECORD_KEY)
    handoff = st.session_state.get(HANDOFF_KEY)
    if handoff:
        handoff["review_complete"] = bool(review_complete)
    if record is not None and remember_handoff(record, handoff, review_complete):
        save_record(st.session_state, st.session_state[OWNER_KEY], record)


def _render_action_bar(state: dict, progress) -> None:
    st.divider()
    left, middle, right = st.columns([2, 1, 1])
    left.markdown(f"**{progress.label}**  \n{progress.blocker or 'Your resume is ready for Apply.'}")
    if middle.button("Regenerate", use_container_width=True, disabled=not progress.needs_rebuild and state.get("reviewed", False),
                     help="Rebuild the resume with your decisions. The model is not run again."):
        with st.spinner("Rebuilding your resume…"):
            ok = _regenerate_from_current_dispositions()
        if ok:
            st.toast("Resume rebuilt with your decisions.")
            st.rerun()
    if progress.can_continue:
        with right:
            primary_action("Continue to application", "pages/3_Applications.py", "tailor_continue")
    else:
        right.button("Continue to application", disabled=True, use_container_width=True, help=progress.blocker)


def _resume_source(owner_id: str):
    """(filename, bytes, label) for the resume to tailor, or None."""
    one_off = st.session_state.get("tailor_one_off")
    if one_off:
        return one_off["name"], one_off["bytes"], f"One-off file for this job: {one_off['name']}"
    record = st.session_state.get(RECORD_KEY) or {}
    meta = record.get("resume")
    data = store_for(owner_id).resume_bytes(meta) if meta else None
    if data:
        return meta["filename"], data, f"{meta['filename']} · version {meta['version']} from your Career Profile"
    return None


def _render_settings() -> None:
    with st.expander("Settings"):
        st.selectbox("Resume length", ["Preserve original length", "1 page", "2 pages"], key="tailor_length")
        st.checkbox("Light touch: only add missing keywords, don't rewrite bullets", key="tailor_conservative")
        one_off = st.file_uploader("Use a different resume file for this job only", type=["pdf", "docx"],
                                   key="tailor_one_off_upload")
        if one_off is not None:
            st.session_state["tailor_one_off"] = {"name": one_off.name, "bytes": one_off.getvalue()}
        if st.session_state.get("tailor_one_off") and st.button("Go back to my profile resume"):
            st.session_state.pop("tailor_one_off", None)
            st.rerun()
        st.caption("Writing model (leave blank to use the configured one)")
        model_choice = st.selectbox("Common models", options=["(custom / env)"] + COMMON_MODELS, key="tailor_model_choice")
        st.text_input("Model id", value="" if model_choice.startswith("(") else model_choice, key="tailor_model")
        st.text_input("API key", type="password", key="tailor_api_key")
        st.text_input("Base URL (optional)", key="tailor_api_base")


def _resume_line(owner_id: str, source) -> bool:
    if source:
        st.markdown(f'<div class="jc-meta">Resume: {escape(source[2])}</div>', unsafe_allow_html=True)
        return True
    st.warning("No resume yet. Import it once in Career Profile and it is reused for every job.")
    st.page_link("pages/1_Profile_Review.py", label="Import your resume →")
    return False


def _existing_handoff(pending: dict):
    """The validated tailored resume already made for this job (kept across sessions), if any."""
    handoff = st.session_state.get(HANDOFF_KEY) or {}
    if not pending or handoff.get("job_id") != pending.get("job_id"):
        return None
    if str(handoff.get("validation_status", "")).upper() == "FAIL" or not os.path.isfile(handoff.get("pdf_path", "")):
        return None
    return handoff


def _render_existing(handoff: dict, main, side) -> None:
    """Don't offer to start over when a usable tailored resume already exists."""
    status = str(handoff.get("validation_status", "")).upper()
    reviewed = bool(handoff.get("review_complete"))
    with main:
        with st.container(border=True):
            st.markdown(
                '<h2 class="jc-card-title">Your tailored resume is ready</h2>'
                f'<p class="jc-meta">Version {handoff.get("version")} · '
                f'{"passed validation" if status == "PASS" else "passed with warnings to read"} · '
                f'{"every change reviewed" if reviewed else "changes not fully reviewed"}</p>',
                unsafe_allow_html=True,
            )
            with st.container(horizontal=True):
                primary_action("Continue to application", "pages/3_Applications.py", "tailor_ready_continue")
                with open(handoff["pdf_path"], "rb") as f:
                    st.download_button("Download PDF", f.read(), file_name=f"tailored_resume_v{handoff.get('version')}.pdf",
                                       mime="application/pdf", key="tailor_ready_download")
                if st.button("Tailor again", key="tailor_ready_redo",
                             help="Creates a new version. The current one stays until the new one passes validation."):
                    st.session_state["tailor_redo"] = True
                    st.rerun()
            st.caption("The change-by-change review for this version wasn't saved. "
                       "Tailor again to review changes one by one.")
    with side:
        st.markdown('<div class="jc-aside"><h3>What happens next</h3>'
                    "<p>Apply checks everything is ready and opens the employer's own application.</p>"
                    "<p>Nothing is submitted for you.</p></div>", unsafe_allow_html=True)


def _render_setup(owner_id: str, pending: dict) -> None:
    source = _resume_source(owner_id)
    main, side = st.columns([2, 1], gap="large")
    ready_resume = _existing_handoff(pending)
    if pending and ready_resume and not st.session_state.get("tailor_redo"):
        _render_existing(ready_resume, main, side)
        return
    if pending:
        with main:
            with st.container(border=True):
                st.markdown('<h2 class="jc-card-title">Create your tailored resume</h2>'
                            '<p class="jc-meta">Job Copilot proposes only changes your verified facts support. '
                            "You review each one before anything is used.</p>", unsafe_allow_html=True)
                ready = _resume_line(owner_id, source)
                if st.button("Create tailored resume", type="primary", disabled=not ready, key="tailor_create"):
                    _run_tailoring(source, pending)
                _render_settings()
                with st.expander("Job description (from the posting)"):
                    st.markdown(st.session_state.get(_JD_SESSION_KEY) or "No description was found for this job.")
        with side:
            st.markdown(
                '<div class="jc-aside"><h3>What happens next</h3>'
                "<p>About a minute to write and check changes against your Career Profile.</p>"
                "<p>Then you review each change beside the exact resume, and continue to Apply.</p></div>",
                unsafe_allow_html=True,
            )
        return

    with main:
        with st.container(border=True):
            st.markdown('<h2 class="jc-card-title">No job selected</h2>'
                        '<p class="jc-meta">Choose a role in Jobs and select <strong>Prepare this application</strong>. '
                        "It opens here with the posting already loaded.</p>", unsafe_allow_html=True)
            if st.button("Find a job", type="primary", key="tailor_find_job"):
                st.switch_page("pages/2_Job_Search.py")
        with st.expander("Tailor for a job that's not in your search results"):
            st.text_area("Paste the job description", height=220, key=_JD_SESSION_KEY)
            ready = _resume_line(owner_id, source)
            if st.button("Create tailored resume", disabled=not ready, key="tailor_create_manual"):
                _run_tailoring(source, pending)
            _render_settings()
    with side:
        st.markdown(
            '<div class="jc-aside"><h3>How Tailor works</h3>'
            "<p>It rewords your existing bullets to match the posting, using only facts you've confirmed.</p>"
            "<p>Requirements you don't meet are listed as missing and never added.</p></div>",
            unsafe_allow_html=True,
        )


def _run_tailoring(source, pending: dict) -> None:
    filename, original_bytes, label = source
    llm_fields = collect_sidebar_llm_fields(
        st.session_state.get("tailor_model", ""), st.session_state.get("tailor_api_key", ""),
        st.session_state.get("tailor_api_base", ""),
    )
    try:
        settings = resolve_settings(model=llm_fields["model"], api_key=llm_fields["api_key"], api_base=llm_fields["api_base"])
    except ValueError as exc:
        st.error(f"The writing model isn't set up: {exc}")
        return
    _reset_review_state()
    try:
        with st.status("Tailoring your resume…", expanded=True) as status:
            state = run_tailoring(
                st.session_state, original_bytes=original_bytes, filename=filename,
                job_description=st.session_state.get(_JD_SESSION_KEY) or "", pending=pending,
                llm=LLMClient(settings),
                target_length=TARGET_LENGTHS.get(st.session_state.get("tailor_length"), "preserve"),
                conservative=bool(st.session_state.get("tailor_conservative")),
                progress=st.write,
                provenance=None if label.startswith("One-off") else (st.session_state.get(RECORD_KEY) or {}).get("provenance"),
                career_profile=None if label.startswith("One-off") else get_career_profile(st.session_state),
            )
            status.update(label="Your tailored resume is ready to review", state="complete")
    except TailoringError as exc:
        st.error(str(exc))
        return
    st.session_state[_STATE_KEY] = state
    st.session_state.pop("tailor_redo", None)
    st.rerun()


def main():
    identity = require_identity()
    st.session_state["artifacts_dir"] = artifacts_dir(identity.owner_id)
    render_app_shell("Tailor")
    render_page_header(
        "Tailor",
        "Review each proposed change against your verified facts. Nothing is used until you decide.",
    )

    render_batch_switcher(job_service_for(st.session_state[OWNER_KEY]))  # spec 011
    pending = st.session_state.get(PENDING_TAILOR_JOB_KEY) or {}
    if pending:
        if sync_pending_job(st.session_state, pending, _JD_SESSION_KEY, _STATE_KEY):
            st.session_state.pop("tailor_redo", None)

    job_id = pending.get("job_id")
    _restore_review(job_id)
    _save_review_if_changed(job_id)
    if _STATE_KEY in st.session_state:
        _render_review_room(pending)
        _save_review_if_changed(job_id)
        with st.expander("Start over for this job"):
            st.caption("Discards the current review. Your Career Profile is not changed.")
            if st.button("Discard and tailor again"):
                _reset_review_state()
                discard_review(st.session_state.get("artifacts_dir"), job_id)
                st.session_state.pop(HANDOFF_KEY, None)
                st.session_state["tailor_redo"] = True
                st.rerun()
        return

    if pending:
        _render_context(pending, None)
    _render_setup(identity.owner_id, pending)


main()
