"""
Streamlit Web UI for the Resume Tailoring pipeline.

Steps 16-20 (spec 002, decision 014): this module now dispatches through
the SAME shared validated-artifact building blocks apps/api/app/tailor/
router.py uses -- a DOCX upload goes through the master-template splice
pipeline (resume_tailorer.docx_export), a PDF-only/no-upload case goes
through the freeform reconstruction path, and BOTH produce a structured
ArtifactValidation, a ResumeChange list, and a FinalApplicationReport via
the same product-layer functions the API calls. Previously this file
ALWAYS used the freeform path, even for a DOCX upload -- the exact
fragmentation problem decision 014 named as the reason Steps 16-20
needed one shared pipeline instead of adapter-specific fixes.

Review (accept/reject/restore/manually edit a change, then regenerate) is
applied locally via resume_tailorer.artifacts.regeneration -- the same
functions the API's regenerate endpoint calls -- rather than through a
network request, since this Streamlit app has no user accounts/database
of its own to route through.
"""

import os
import sys
import tempfile
from pathlib import Path

# Streamlit Community Cloud runs `streamlit run <main file path>` and adds
# only that FILE's own directory to sys.path (like `python script.py`
# always has) -- never the repo layout this app actually needs, which is
# product/ (the parent of resume_tailorer/) on the path so `import
# resume_tailorer.xxx` resolves. Locally this is normally handled by
# setting PYTHONPATH by hand before running Streamlit; Cloud has no
# equivalent setting, so the app does it itself, once, before any
# resume_tailorer import below. Safe to run twice (inserting the same
# path again is a no-op check).
_PRODUCT_DIR = str(Path(__file__).resolve().parent.parent)
if _PRODUCT_DIR not in sys.path:
    sys.path.insert(0, _PRODUCT_DIR)

from dotenv import load_dotenv
import streamlit as st

from resume_tailorer.llm.settings import apply_secret_settings

# Loads LLM_MODEL/LLM_API_KEY/LLM_API_BASE from a local .env file (gitignored)
# if one exists, so a real key never has to be pasted into the sidebar or
# exported by hand in every new terminal. Does nothing if no .env is present
# or the values are already set in the real environment (load_dotenv never
# overrides an existing env var by default).
load_dotenv()

# On Streamlit Community Cloud there is no .env file at all -- secrets are
# configured through the app's own Settings -> Secrets page instead, and
# surfaced to the running app as st.secrets. Filling any STILL-missing
# LLM_MODEL/LLM_API_KEY/LLM_API_BASE from there (never overriding a value
# already set locally) means the exact same app.py runs unchanged in both
# places. st.secrets raises if no secrets.toml exists at all (the normal
# case for local development), so this is deliberately best-effort.
try:
    apply_secret_settings(st.secrets)
except Exception:
    pass

from resume_tailorer.parsers import ResumeParser
from resume_tailorer.session_profile import RESUME_UPLOAD, has_verified_profile, set_career_profile
from resume_tailorer.tailoring_session import publish_artifact_handoff, sync_pending_job
from resume_tailorer.analyzers import JobAnalyzer, ResumeBenchmarker, GapAnalyzer
from resume_tailorer.tailorer import ResumeTailorer, ResumeTailoringOptimizer
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer
from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.diff_generator import DiffGenerator
from resume_tailorer.llm.settings import resolve_settings
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.ui import COMMON_MODELS, collect_sidebar_llm_fields
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.docx_export import run_docx_tailoring_pipeline
from resume_tailorer.analyzers.gap_analyzer import find_unsupported_claims
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import FidelityMode, ValidationStatus
from resume_tailorer.artifacts.regeneration import (
    apply_dispositions_to_text,
    regenerate_docx_artifact,
    regenerate_freeform_artifact,
    validate_manual_text,
)
from resume_tailorer.artifacts.report import build_final_report
from resume_tailorer.ui.artifact_review import visible_changes
from resume_tailorer.ui import build_workflow_state, render_app_shell, render_page_header
from resume_tailorer.ui.tailoring_view import (
    build_tailoring_summary,
    group_changes,
    safe_default_dispositions,
)


st.set_page_config(page_title="Resume Tailorer", page_icon="\U0001F4C4", layout="wide")

_JD_SESSION_KEY = "job_description_text"
_STATE_KEY = "artifact_run_state"

# Disposition options offered per change. String values match
# resume_tailorer.artifacts.models.ChangeDisposition exactly.
_DISPOSITION_OPTIONS = ["ACCEPTED", "REJECTED", "MANUALLY_EDITED"]


def _save_uploaded_file(uploaded_file) -> str:
    """Persist an uploaded Streamlit file to a temp path and return its path."""
    suffix = os.path.splitext(uploaded_file.name)[1]
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return tmp_path


def _reset_review_state() -> None:
    st.session_state.pop(_STATE_KEY, None)


def _regenerate_from_current_dispositions() -> None:
    """Apply the current per-change disposition/manual-text choices and
    regenerate the artifact -- never re-invokes the LLM tailorer, so a
    human's accept/reject/manual-edit choices are exactly what appears in
    the output (spec 002 section 10)."""
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
                st.error(f"Manual edit for '{change.original_text[:40]}...' cannot be empty.")
                return
            issues = validate_manual_text(change.original_text, manual_text, state["profile"])
            if issues:
                st.error(
                    f"Manual edit for '{change.original_text[:40]}...' failed safety checks: "
                    + "; ".join(issues)
                )
                return
        # proposed_text is left as the AI's original proposal -- never
        # overwritten -- so regenerate_freeform_artifact can still find it
        # verbatim in the run's baseline text. See ResumeChange.manual_text.
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
            )
        finally:
            os.remove(tmp_path)
        docx_bytes = None

    unsupported_claims = find_unsupported_claims(gap_report, tailored_text)
    tailored_alignment, _matched, _missing = ResumeTailoringOptimizer._score_resume(
        tailored_text, state["job_analysis"], profile
    )
    report = build_final_report(
        candidate_fit=None,
        fit_breakdown={},
        original_alignment=state["original_alignment"],
        tailored_alignment=tailored_alignment,
        gap_report=gap_report,
        validation=validation,
        artifacts=(),
        company="",
        role="Target Role",
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
        version=state.get("version", 1) + 1,
    )
    publish_artifact_handoff(
        st.session_state, pdf_bytes=pdf_bytes, validation_status=validation.status.value,
        tailored_alignment=tailored_alignment, version=state["version"],
    )


def _render_review_controls() -> None:
    state = st.session_state[_STATE_KEY]
    report = state["report"]
    safe_defaults = safe_default_dispositions(state["changes"], report.true_gaps)
    if safe_defaults and not state.get("gap_blocks_applied"):
        state["dispositions"].update(safe_defaults)
        state["gap_blocks_applied"] = True
        _regenerate_from_current_dispositions()
        state["reviewed"] = False
        st.rerun()
    summary = build_tailoring_summary(state)
    metrics = st.columns(3)
    metrics[0].metric(summary.candidate_fit.label, summary.candidate_fit.value)
    metrics[1].metric(summary.resume_alignment.label, summary.resume_alignment.value)
    metrics[2].metric("Edits to review", summary.review_count)
    st.caption("Candidate fit measures your background. Resume alignment measures how clearly this resume presents it.")

    status = report.validation.status
    if status is ValidationStatus.PASS:
        st.success("Validation passed. This artifact is application-ready.")
    elif status is ValidationStatus.WARNING:
        st.warning("Validation passed with WARNINGS -- review before submitting:")
        for finding in report.validation.findings:
            st.write(f"- **{finding.code}**: {finding.message}")
    else:
        st.error("Validation FAILED -- do not submit this artifact as-is:")
        for finding in report.validation.findings:
            st.write(f"- **{finding.code}**: {finding.message}")

    fidelity_label = "Preserved exactly" if report.fidelity_mode is FidelityMode.PRESERVED else "Reconstructed; visual details may differ"
    st.caption(f"Document fidelity: {fidelity_label}.")

    review, artifact = st.columns([1.1, .9], gap="large")
    with review:
        st.subheader("Review proposed edits")
        advanced = st.checkbox("Show all audited changes", value=False)
        shown = visible_changes(state["changes"], advanced=advanced)
        groups = group_changes(shown, report.true_gaps)
        if groups.true_gaps:
            st.markdown('<div class="jc-status blocked"><strong>Missing, never added</strong></div>', unsafe_allow_html=True)
            for gap in groups.true_gaps:
                st.write(f"- {gap}")
        for change in groups.blocked:
            st.warning(
                f"Blocked proposal kept the original: {change.proposed_text} "
                f"(unsupported requirement: {change.job_requirement or 'true gap'})."
            )
        if not groups.reviewable:
            st.info("No evidence-backed edits remain to review.")
        for change in groups.reviewable:
            with st.container(border=True):
                st.markdown(f"**{change.category.value.replace('_', ' ').title()}** · {change.reason}")
                st.caption(f"Original · {change.original_text}")
                st.write(f"**Proposed** · {change.proposed_text}")
                if change.job_requirement:
                    st.markdown(f"**Requirement** · {change.job_requirement}")
                st.markdown(
                    f"**Evidence** · {change.evidence_text or 'No evidence recorded'}  \n"
                    f"Source: {change.evidence_source or 'Not recorded'} · Validation: {change.validation_status.value}"
                )
                current = state["dispositions"].get(change.change_id, "ACCEPTED")
                labels = {"ACCEPTED": "Accept edit", "MANUALLY_EDITED": "Edit manually", "REJECTED": "Keep original"}
                chosen_label = st.radio(
                    "Decision",
                    list(labels.values()),
                    index=list(labels).index(current) if current in labels else 0,
                    key=f"disposition_{change.change_id}",
                    horizontal=True,
                )
                choice = next(key for key, label in labels.items() if label == chosen_label)
                state["dispositions"][change.change_id] = choice
                if choice == "MANUALLY_EDITED":
                    state["manual_texts"][change.change_id] = st.text_area(
                        "Your edit", value=state["manual_texts"].get(change.change_id, change.proposed_text), key=f"manual_{change.change_id}"
                    )
        if st.button("Apply decisions and rebuild", type="primary", use_container_width=True):
            _regenerate_from_current_dispositions()
            st.rerun()

    with artifact:
        st.subheader("Resume and validation")
        st.text_area("Tailored resume", state["tailored_text"], height=460)
        _render_diagnostics_and_download(state)


def _render_diagnostics_and_download(state: dict) -> None:
    report = state["report"]

    with st.expander("Diagnostics"):
        st.write(f"Fidelity: {report.fidelity_mode}")
        st.write(f"Original page count: {report.original_page_count}")
        st.write(f"Tailored page count: {report.tailored_page_count}")
        if report.unsupported_claims:
            st.warning("Unsupported claims found in the tailored text:")
            for claim in report.unsupported_claims:
                st.write(f"- {claim}")
        st.write("All validation findings:")
        for finding in report.validation.findings:
            st.write(f"- [{finding.severity}] {finding.code}: {finding.message}")

    status = report.validation.status
    docx_bytes = state.get("docx_bytes")
    pdf_bytes = state.get("pdf_bytes")

    if status is ValidationStatus.FAIL:
        st.error("This artifact failed validation and is not available as an application-ready download.")
        return

    if status is ValidationStatus.WARNING:
        st.warning("Downloading an artifact with unresolved warnings -- review them above first.")

    name = state.get("candidate_name", "resume").replace(" ", "_")
    if docx_bytes:
        st.download_button(
            "Download tailored resume (DOCX)", data=docx_bytes,
            file_name=f"{name}_tailored_resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if pdf_bytes:
        st.download_button(
            "Download tailored resume (PDF)", data=pdf_bytes,
            file_name=f"{name}_tailored_resume.pdf", mime="application/pdf",
        )


def main():
    render_app_shell("Tailoring Studio", build_workflow_state(st.session_state))
    render_page_header(
        "Tailoring Studio",
        "Shape a job-specific resume from verified evidence. Review every meaningful edit before it becomes an application artifact.",
    )

    pending = st.session_state.get(PENDING_TAILOR_JOB_KEY)
    if pending:
        fit = pending.get("candidate_fit") or {}
        overall = fit.get("overall_fit")
        fit_label = f"{round(overall)}%" if isinstance(overall, (int, float)) else "N/A"
        st.info(
            f"Continuing from Job Search: **{pending.get('title', 'Job')}** @ "
            f"**{pending.get('company', '')}** — Candidate Fit {fit_label}."
        )
        sync_pending_job(st.session_state, pending, _JD_SESSION_KEY, _STATE_KEY)

    with st.sidebar:
        st.subheader("Resume evidence")
        resume_file = st.file_uploader(
            "Resume file (PDF or DOCX)", type=["pdf", "docx", "doc"]
        )

        st.subheader("Target role")
        job_description = st.text_area(
            "Job description text", height=250, key=_JD_SESSION_KEY
        )

        st.subheader("Artifact settings")
        length_choice_ui = st.selectbox(
            "Target resume length",
            options=["1 page", "2 pages", "Preserve original length"],
            index=2,
        )
        target_length_map = {
            "1 page": "1_page",
            "2 pages": "2_page",
            "Preserve original length": "preserve",
        }
        target_length = target_length_map[length_choice_ui]

        conservative_mode = st.checkbox(
            "Conservative mode: only add missing keywords, don't rewrite bullets",
            value=False,
            help=(
                "Leaves your existing wording and structure untouched and only "
                "weaves in the specific ATS keywords the job posting is missing, "
                "instead of a full rewrite."
            ),
        )

        with st.expander("Model settings"):
            st.caption("Leave blank to use the configured environment.")
            model_choice = st.selectbox("Common models", options=["(custom / env)"] + COMMON_MODELS)
            model_input = st.text_input("Model id", value="" if model_choice.startswith("(") else model_choice)
            api_key_input = st.text_input("API key", type="password")
            api_base_input = st.text_input("Base URL (optional)")

        run_clicked = st.button("Build tailored resume", type="primary", use_container_width=True)

    if run_clicked:
        _reset_review_state()

    if _STATE_KEY in st.session_state:
        _render_review_controls()
        return

    if not run_clicked:
        st.markdown(
            '<div class="jc-panel"><h3>Start with two sources</h3><p>Upload your resume and paste the target job description. Job Copilot will propose only edits supported by your existing evidence.</p></div>',
            unsafe_allow_html=True,
        )
        return

    if not resume_file:
        st.error("Please upload a resume file (PDF or DOCX) before continuing.")
        return

    if not job_description or not job_description.strip():
        st.error("Please paste a job description before continuing.")
        return

    llm_fields = collect_sidebar_llm_fields(model_input, api_key_input, api_base_input)
    try:
        settings = resolve_settings(
            model=llm_fields["model"],
            api_key=llm_fields["api_key"],
            api_base=llm_fields["api_base"],
        )
    except ValueError as exc:
        st.error(str(exc))
        if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("LLM_API_KEY"):
            st.info(
                "ANTHROPIC_API_KEY is set but no longer used alone. "
                "Set LLM_MODEL=anthropic/claude-3-5-sonnet-20241022 and "
                "LLM_API_KEY to your Anthropic key."
            )
        return

    llm = LLMClient(settings)

    # --- Step 1: Parse resume --------------------------------------------------
    resume_path = None
    original_bytes = resume_file.getvalue()
    suffix = os.path.splitext(resume_file.name)[1].lower()
    is_docx = suffix == ".docx"
    try:
        with st.spinner("Parsing resume..."):
            resume_path = _save_uploaded_file(resume_file)
            parser = ResumeParser()
            profile = set_career_profile(st.session_state, parser.parse(resume_path), RESUME_UPLOAD)
            try:
                raw_resume_text = parser.get_raw_text(resume_path)
            except ValueError:
                raw_resume_text = ""
            style_hints = parser.extract_style_hints(raw_resume_text, file_path=resume_path)
        if has_verified_profile(st.session_state):
            st.success(f"Using your verified Fact Vault facts for {profile.name}.")
        else:
            st.success(f"Resume parsed for {profile.name}.")
    except Exception as exc:
        st.error(f"Failed to parse resume: {exc}")
        return
    finally:
        if resume_path and os.path.exists(resume_path):
            try:
                os.remove(resume_path)
            except OSError:
                pass

    # --- Step 2: Analyze job description ---------------------------------------
    try:
        with st.spinner("Analyzing job description..."):
            job_analysis = JobAnalyzer().analyze(job_description)
        st.success("Job description analyzed.")
    except Exception as exc:
        st.error(f"Failed to analyze job description: {exc}")
        return

    # --- Step 3: Benchmark original resume --------------------------------------
    try:
        with st.spinner("Benchmarking your original resume against this job..."):
            benchmark = ResumeBenchmarker().benchmark(profile, job_analysis)
    except Exception as exc:
        st.error(f"Failed to benchmark resume: {exc}")
        return

    # --- Step 4: Gap analysis ---------------------------------------------------
    try:
        with st.spinner("Running gap analysis..."):
            gap_report = GapAnalyzer().analyze(profile, job_analysis, benchmark)
    except Exception as exc:
        st.error(f"Failed to run gap analysis: {exc}")
        return

    # --- Steps 13-20: tailor + generate a validated artifact --------------------
    # A DOCX upload MUST reach the master-template splice pipeline -- never the
    # freeform reconstruction path, which would discard the original's exact
    # formatting (decision 006, decision 014).
    baseline_text = ""
    tailored_alignment = benchmark.original_match_score
    try:
        if is_docx:
            with st.spinner("Tailoring and generating your resume (this may take a moment)..."):
                docx_result = run_docx_tailoring_pipeline(
                    original_bytes, profile, job_analysis, gap_report,
                    bullet_tailorer=DocxBulletTailorer(llm=llm),
                    convert_to_pdf=True,
                )
            tailored_text = docx_result.tailored_scoring_text
            tailored_alignment, _matched, _missing = ResumeTailoringOptimizer._score_resume(
                tailored_text, job_analysis, profile
            )
            changes = list(docx_result.changes)
            validation = docx_result.validation
            docx_bytes = docx_result.docx_bytes
            pdf_bytes = docx_result.pdf_bytes
            fidelity_mode = FidelityMode.PRESERVED
        else:
            with st.spinner("Tailoring resume with the configured LLM..."):
                initial_tailored = ResumeTailorer(llm=llm).tailor(
                    profile, job_analysis, gap_report, conservative=conservative_mode
                )
            with st.spinner("Optimizing tailored resume for alignment..."):
                optimization_result = ResumeTailoringOptimizer(llm=llm).optimize(
                    profile, job_analysis, initial_tailored, gap_report, conservative=conservative_mode
                )
            tailored_text = optimization_result.tailored_resume
            baseline_text = tailored_text
            tailored_alignment = optimization_result.final_score
            changes = build_freeform_changes(profile, tailored_text, gap_report)
            with st.spinner("Generating and validating PDF..."):
                pdf_path = PDFGenerator().generate(
                    tailored_text, profile.name, target_length=target_length, style_hints=style_hints,
                )
                validation = PDFValidator().validate_artifact(
                    pdf_path, profile=profile, expected_page_count=None, accepted_changes=changes,
                )
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
            docx_bytes = None
            fidelity_mode = FidelityMode.RECONSTRUCTED
    except RuntimeError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Tailoring failed: {exc}")
        return

    unsupported_claims = find_unsupported_claims(gap_report, tailored_text)
    report = build_final_report(
        candidate_fit=None,
        fit_breakdown={},
        original_alignment=benchmark.original_match_score,
        tailored_alignment=tailored_alignment,
        gap_report=gap_report,
        validation=validation,
        artifacts=(),
        company="",
        role="Target Role",
        fidelity_mode=fidelity_mode,
        unsupported_claims=unsupported_claims,
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
        "fidelity_mode": fidelity_mode,
        "changes": changes,
        "dispositions": {},
        "manual_texts": {},
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
    )
    st.rerun()


if __name__ == "__main__":
    main()
