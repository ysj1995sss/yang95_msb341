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
import tempfile
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

from resume_tailorer.parsers import ResumeParser
from resume_tailorer.identity import artifacts_dir
from resume_tailorer.profile_import import RECORD_KEY, store_for
from resume_tailorer.ui.auth_gate import require_identity
from resume_tailorer.session_profile import RESUME_UPLOAD, set_career_profile
from resume_tailorer.tailoring_session import HANDOFF_KEY, publish_artifact_handoff, sync_pending_job
from resume_tailorer.analyzers import JobAnalyzer, ResumeBenchmarker, GapAnalyzer
from resume_tailorer.tailorer import ResumeTailorer, ResumeTailoringOptimizer
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.llm.settings import resolve_settings
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.ui import COMMON_MODELS, collect_sidebar_llm_fields
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.docx_export import run_docx_tailoring_pipeline
from resume_tailorer.analyzers.gap_analyzer import find_unsupported_claims
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.length_control import (
    build_freeform_artifact,
    correct_docx_length_once,
    max_pages_label,
)
from resume_tailorer.artifacts.models import FidelityMode, ValidationStatus
from resume_tailorer.artifacts.regeneration import (
    regenerate_docx_artifact,
    regenerate_freeform_artifact,
    validate_manual_text,
)
from resume_tailorer.artifacts.report import build_final_report
from resume_tailorer.ui.artifact_review import visible_changes
from resume_tailorer.ui import chip, render_app_shell, render_page_header, render_progress
from resume_tailorer.ui.shell import primary_action
from resume_tailorer.ui.design_system import ProgressStep
from resume_tailorer.ui.pdf_preview import pdf_page_images
from resume_tailorer.ui.tailor_progress import (
    DECISION_DONE,
    VERBS,
    artifact_status_text,
    artifact_tone,
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


def _reset_review_state() -> None:
    st.session_state.pop(_STATE_KEY, None)
    st.session_state.pop(_FOCUS_KEY, None)


def _regenerate_from_current_dispositions() -> bool:
    """Apply the current per-change decisions and rebuild the artifact. Never
    re-invokes the model, so the output is exactly what the user decided
    (spec 002 section 10). Returns False when a manual edit is rejected."""
    state = st.session_state[_STATE_KEY]
    changes = state["changes"]
    dispositions = state["dispositions"]
    manual_texts = state["manual_texts"]

    from dataclasses import replace as _replace
    from resume_tailorer.artifacts.models import ChangeDisposition

    updated_changes = []
    for change in changes:
        disposition_str = dispositions.get(change.change_id, str(change.disposition))
        disposition = ChangeDisposition(disposition_str)
        manual_text = None
        if disposition == ChangeDisposition.MANUALLY_EDITED:
            manual_text = manual_texts.get(change.change_id, "").strip()
            if not manual_text:
                st.error(f"Your edit for '{change.original_text[:40]}…' is empty. Write the text or keep the original.")
                return False
            issues = validate_manual_text(change.original_text, manual_text, state["profile"])
            if issues:
                st.error(
                    f"Your edit for '{change.original_text[:40]}…' adds something we can't verify: "
                    + "; ".join(issues)
                )
                return False
        # proposed_text stays the model's untouched proposal so the freeform
        # path can still find it in the baseline text (ResumeChange.manual_text).
        updated_changes.append(_replace(change, disposition=disposition, manual_text=manual_text))

    profile = state["profile"]
    gap_report = state["gap_report"]

    if state["source_kind"] == "DOCX":
        result = regenerate_docx_artifact(
            original_docx_bytes=state["original_bytes"],
            changes=updated_changes,
            profile=profile,
            gap_report=gap_report,
            convert_to_pdf=True,
        )
        tailored_text = result.tailored_scoring_text
        validation = result.validation
        docx_bytes = result.docx_bytes
        pdf_bytes = result.pdf_bytes
    else:
        pdf_bytes, tailored_text = regenerate_freeform_artifact(
            baseline_tailored_text=state["baseline_text"],
            changes=updated_changes,
            profile=profile,
            target_length=state["target_length"],
            style_hints=state["style_hints"] or {},
            company="",
            role="",
        )
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            validation = PDFValidator().validate_artifact(
                tmp_path, profile=profile, expected_page_count=None, accepted_changes=updated_changes,
                target_length=max_pages_label(state["target_length"], state["style_hints"]),
            )
        finally:
            os.remove(tmp_path)
        docx_bytes = None

    unsupported_claims = find_unsupported_claims(gap_report, tailored_text)
    tailored_alignment, _matched, _missing = ResumeTailoringOptimizer._score_resume(
        tailored_text, state["job_analysis"], profile
    )
    report = build_final_report(
        candidate_fit=state.get("candidate_fit"),
        fit_breakdown={},
        original_alignment=state["original_alignment"],
        tailored_alignment=tailored_alignment,
        gap_report=gap_report,
        validation=validation,
        artifacts=(),
        company=state.get("company", ""),
        role=state.get("role") or "Target Role",
        fidelity_mode=state["fidelity_mode"],
        unsupported_claims=unsupported_claims,
    )

    state.update(
        changes=updated_changes,
        tailored_text=tailored_text,
        validation=validation,
        docx_bytes=docx_bytes,
        pdf_bytes=pdf_bytes,
        report=report,
        reviewed=True,
        dirty=False,
        version=state.get("version", 1) + 1,
    )
    publish_artifact_handoff(
        st.session_state, pdf_bytes=pdf_bytes, validation_status=validation.status.value,
        tailored_alignment=tailored_alignment, version=state["version"],
        folder=st.session_state.get("artifacts_dir"),
    )
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
    alignment = _percent(report.tailored_alignment) if report else "Not built yet"
    st.markdown(
        f'<div class="jc-panel"><div class="jc-eyebrow">{escape(company) or "Pasted job description"}</div>'
        f'<h2 style="margin:.1rem 0 .5rem">{escape(title)}</h2>'
        f'{chip("Candidate fit " + _fit_label(pending), "action")}'
        f'{chip("Resume alignment " + alignment)}'
        f'{chip(artifact_status_text(status), tone)}'
        f'<p class="jc-meta" style="margin-top:.35rem">Candidate fit measures your background. '
        f"Resume alignment measures how clearly this resume shows it. They are never combined.</p></div>",
        unsafe_allow_html=True,
    )


def _render_change_focus(state: dict, change, profile) -> None:
    current = state["dispositions"].get(change.change_id)
    decided = change.change_id in state["decided"]
    with st.container(border=True):
        status_text = DECISION_DONE.get(current, "Not reviewed yet") if decided else "Not reviewed yet"
        st.markdown(
            f'<div class="jc-eyebrow">Review this change · {escape(status_text)}</div>',
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

        if groups.true_gaps or groups.blocked:
            st.markdown("### Missing, never added")
            st.markdown(
                '<div class="jc-status blocked">These requirements aren\'t in your verified experience. '
                "Job Copilot will not add them.</div>",
                unsafe_allow_html=True,
            )
            for gap in groups.true_gaps:
                text = gap if len(gap) <= 140 else gap[:137].rsplit(" ", 1)[0] + "…"
                st.markdown(f"- Missing from your experience: {text}")
            for change in groups.blocked:
                st.markdown(
                    f"- Blocked a proposed line that claimed *{change.job_requirement or 'an unsupported requirement'}*; "
                    "the original was kept."
                )

    with preview:
        st.markdown('<span class="jc-sticky-marker"></span>', unsafe_allow_html=True)
        _render_preview(state)

    _render_action_bar(state, progress)


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
        st.write(f"Resume alignment: {_percent(report.original_alignment)} before, {_percent(report.tailored_alignment)} after.")
        if report.unsupported_claims:
            st.write("Unsupported claims found and blocked:")
            for claim in report.unsupported_claims:
                st.write(f"- {claim}")
        for finding in report.validation.findings:
            st.write(f"- {finding.message}")


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


def _render_setup(owner_id: str, pending: dict) -> None:
    source = _resume_source(owner_id)
    main, side = st.columns([2, 1], gap="large")
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
    filename, original_bytes, _label = source
    job_description = st.session_state.get(_JD_SESSION_KEY) or ""
    if not job_description.strip():
        st.error("Add the job description first: choose a job in Jobs, or paste one above.")
        return
    target_length = {"1 page": "1_page", "2 pages": "2_page"}.get(st.session_state.get("tailor_length"), "preserve")
    conservative_mode = bool(st.session_state.get("tailor_conservative"))
    llm_fields = collect_sidebar_llm_fields(
        st.session_state.get("tailor_model", ""), st.session_state.get("tailor_api_key", ""),
        st.session_state.get("tailor_api_base", ""),
    )
    try:
        settings = resolve_settings(model=llm_fields["model"], api_key=llm_fields["api_key"], api_base=llm_fields["api_base"])
    except ValueError as exc:
        st.error(f"The writing model isn't set up: {exc}")
        return
    llm = LLMClient(settings)
    _reset_review_state()

    suffix = os.path.splitext(filename)[1].lower()
    is_docx = suffix == ".docx"
    fd, resume_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(original_bytes)
        with st.status("Tailoring your resume…", expanded=True) as status:
            st.write("Reading your resume")
            parser = ResumeParser()
            profile = set_career_profile(st.session_state, parser.parse(resume_path), RESUME_UPLOAD)
            try:
                raw_resume_text = parser.get_raw_text(resume_path)
            except ValueError:
                raw_resume_text = ""
            style_hints = parser.extract_style_hints(raw_resume_text, file_path=resume_path)

            st.write("Reading the job description")
            job_analysis = JobAnalyzer().analyze(job_description)
            benchmark = ResumeBenchmarker().benchmark(profile, job_analysis)
            gap_report = GapAnalyzer().analyze(profile, job_analysis, benchmark)

            st.write("Writing and checking changes (about a minute)")
            baseline_text = ""
            if is_docx:
                docx_result = run_docx_tailoring_pipeline(
                    original_bytes, profile, job_analysis, gap_report,
                    bullet_tailorer=DocxBulletTailorer(llm=llm), convert_to_pdf=True,
                )
                docx_result = correct_docx_length_once(
                    original_docx_bytes=original_bytes, docx_result=docx_result,
                    profile=profile, gap_report=gap_report, llm=llm,
                )
                tailored_text = docx_result.tailored_scoring_text
                tailored_alignment, _m, _x = ResumeTailoringOptimizer._score_resume(tailored_text, job_analysis, profile)
                changes = list(docx_result.changes)
                validation = docx_result.validation
                docx_bytes, pdf_bytes = docx_result.docx_bytes, docx_result.pdf_bytes
                fidelity_mode = FidelityMode.PRESERVED
            else:
                initial = ResumeTailorer(llm=llm).tailor(profile, job_analysis, gap_report, conservative=conservative_mode)
                optimization = ResumeTailoringOptimizer(llm=llm).optimize(
                    profile, job_analysis, initial, gap_report, conservative=conservative_mode
                )
                tailored_text = optimization.tailored_resume
                tailored_alignment = optimization.final_score
                changes = build_freeform_changes(profile, tailored_text, gap_report)
                pdf_bytes, validation, tailored_text, changes, _attempts = build_freeform_artifact(
                    tailored_text=tailored_text, changes=changes, profile=profile,
                    target_length=target_length, style_hints=style_hints, llm=llm,
                )
                baseline_text = tailored_text
                docx_bytes = None
                fidelity_mode = FidelityMode.RECONSTRUCTED
            status.update(label="Your tailored resume is ready to review", state="complete")
    except RuntimeError as exc:
        st.error(f"{exc} Try again in a minute.")
        return
    except Exception as exc:
        st.error(f"Tailoring didn't finish: {exc}. Your profile and job are unchanged; try again.")
        return
    finally:
        try:
            os.remove(resume_path)
        except OSError:
            pass

    fit = (pending.get("candidate_fit") or {}).get("overall_fit")
    candidate_fit = fit / 100 if isinstance(fit, (int, float)) else None
    report = build_final_report(
        candidate_fit=candidate_fit,
        fit_breakdown={},
        original_alignment=benchmark.original_match_score,
        tailored_alignment=tailored_alignment,
        gap_report=gap_report,
        validation=validation,
        artifacts=(),
        company=pending.get("company", ""),
        role=pending.get("title") or "Target Role",
        fidelity_mode=fidelity_mode,
        unsupported_claims=find_unsupported_claims(gap_report, tailored_text),
    )
    st.session_state[_STATE_KEY] = {
        "source_kind": "DOCX" if is_docx else "PDF",
        "original_bytes": original_bytes,
        "baseline_text": baseline_text,
        "target_length": target_length,
        "style_hints": style_hints,
        "profile": profile,
        "gap_report": gap_report,
        "job_analysis": job_analysis,
        "original_alignment": benchmark.original_match_score,
        "candidate_fit": candidate_fit,
        "company": pending.get("company", ""),
        "role": pending.get("title", ""),
        "fidelity_mode": fidelity_mode,
        "changes": changes,
        "dispositions": {},
        "manual_texts": {},
        "decided": set(),
        "dirty": False,
        "tailored_text": tailored_text,
        "validation": validation,
        "docx_bytes": docx_bytes,
        "pdf_bytes": pdf_bytes,
        "report": report,
        "candidate_name": profile.name,
        "reviewed": False,
        "version": 1,
    }
    publish_artifact_handoff(
        st.session_state, pdf_bytes=pdf_bytes, validation_status=validation.status.value,
        tailored_alignment=tailored_alignment, version=1,
        folder=st.session_state.get("artifacts_dir"),
    )
    st.rerun()


def main():
    identity = require_identity()
    st.session_state["artifacts_dir"] = artifacts_dir(identity.owner_id)
    render_app_shell("Tailor")
    render_page_header(
        "Tailor",
        "Review each proposed change against your verified facts. Nothing is used until you decide.",
    )

    pending = st.session_state.get(PENDING_TAILOR_JOB_KEY) or {}
    if pending:
        sync_pending_job(st.session_state, pending, _JD_SESSION_KEY, _STATE_KEY)

    if _STATE_KEY in st.session_state:
        _render_review_room(pending)
        with st.expander("Start over for this job"):
            st.caption("Discards the current review. Your Career Profile is not changed.")
            if st.button("Discard and tailor again"):
                _reset_review_state()
                st.session_state.pop(HANDOFF_KEY, None)
                st.rerun()
        return

    if pending:
        _render_context(pending, None)
    _render_setup(identity.owner_id, pending)


main()
