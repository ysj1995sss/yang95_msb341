"""
Streamlit Web UI for the Resume Tailoring pipeline (Task 12).

Ties together the full pipeline built in Tasks 1-11:

    upload resume + job description
        -> ResumeParser.parse                (Task 2)
        -> JobAnalyzer.analyze                (Task 4)
        -> ResumeBenchmarker.benchmark        (Task 5)
        -> GapAnalyzer.analyze                (Task 6)
        -> ResumeTailorer.tailor              (Task 7, LLM via LLMClient)
        -> ResumeTailoringOptimizer.optimize  (Task 9)
        -> PDFGenerator.generate              (Task 10)
        -> PDFValidator.validate              (Task 10)
        -> ReportGenerator.generate_report    (Task 11)

This module only orchestrates the components above. It performs no
scoring, classification, or content generation of its own, and it never
alters or bypasses the fabrication guardrails built into ResumeTailorer
and ResumeTailoringOptimizer.

NOTE ON THE PLAN'S SAMPLE CODE (lines 1887-2006): the plan's sample
referenced `ReportGenerator.generate()`, `ValidationResult.errors`, and
assumed slightly different call signatures. Those names drifted from
what Tasks 5-11 actually implemented. This file uses the REAL signatures
verified by reading the actual source (see report for details); the
plan's sample served only as a guide to the overall UI flow.
"""

import os
import tempfile

import streamlit as st

from resume_tailorer.parsers import ResumeParser
from resume_tailorer.analyzers import JobAnalyzer, ResumeBenchmarker, GapAnalyzer
from resume_tailorer.tailorer import ResumeTailorer, ResumeTailoringOptimizer
from resume_tailorer.pdf import PDFGenerator, PDFValidator
from resume_tailorer.report_generator import ReportGenerator
from resume_tailorer.diff_generator import DiffGenerator
from resume_tailorer.llm.settings import resolve_settings
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.llm.ui import COMMON_MODELS, collect_sidebar_llm_fields


st.set_page_config(page_title="Resume Tailorer", page_icon="\U0001F4C4", layout="wide")


def _save_uploaded_file(uploaded_file) -> str:
    """Persist an uploaded Streamlit file to a temp path and return its path."""
    suffix = os.path.splitext(uploaded_file.name)[1]
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return tmp_path


def main():
    st.title("Resume Tailorer")
    st.caption(
        "Upload your resume and a job description. The pipeline tailors your "
        "resume to the role using ONLY facts already in your resume — it never "
        "fabricates experience, skills, or credentials."
    )

    with st.sidebar:
        st.header("1. Upload your resume")
        resume_file = st.file_uploader(
            "Resume file (PDF or DOCX)", type=["pdf", "docx", "doc"]
        )

        st.header("2. Paste the job description")
        job_description = st.text_area("Job description text", height=250)

        st.header("3. Choose the target resume length")
        # Defaults to "Preserve original length" (index=2): the base rule
        # is to match whatever length/style the user actually uploaded,
        # not to assume everyone wants a fixed 1-page resume regardless of
        # how long their real one is.
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

        st.header("4. Model provider")
        st.caption(
            "Optional: leave blank to use LLM_MODEL / LLM_API_KEY / LLM_API_BASE "
            "from the environment."
        )
        model_choice = st.selectbox(
            "Common models (helper)",
            options=["(custom / env)"] + COMMON_MODELS,
        )
        model_input = st.text_input(
            "Model id",
            value="" if model_choice.startswith("(") else model_choice,
            help=(
                "Examples: openai/gpt-4o, anthropic/claude-3-5-sonnet-20241022, "
                "gemini/gemini-1.5-pro"
            ),
        )
        api_key_input = st.text_input("API key", type="password")
        api_base_input = st.text_input(
            "Base URL (optional)",
            help="Azure / Ollama / proxy / OpenRouter-compatible endpoints",
        )

        run_clicked = st.button("Tailor my resume", type="primary")

    if not run_clicked:
        st.info("Upload a resume, paste a job description, and click **Tailor my resume**.")
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
    try:
        with st.spinner("Parsing resume..."):
            resume_path = _save_uploaded_file(resume_file)
            parser = ResumeParser()
            profile = parser.parse(resume_path)

            # Extract the raw resume text so we can derive style hints
            # (bullet character, heading style) from the source formatting.
            # get_raw_text() is the same public dispatch ResumeParser.parse()
            # uses internally, so there's a single source of truth for
            # file-type dispatch.
            try:
                raw_resume_text = parser.get_raw_text(resume_path)
            except ValueError:
                raw_resume_text = ""
            # file_path=resume_path additionally detects the original's
            # page count and font family straight from the PDF structure,
            # so "Preserve original length" actually preserves length and
            # the output uses a similar font family.
            style_hints = parser.extract_style_hints(raw_resume_text, file_path=resume_path)
        st.session_state["career_profile"] = profile
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

    # --- Step 5: Tailor resume (live LLM call) ----------------------------------
    try:
        with st.spinner("Tailoring resume with the configured LLM..."):
            tailored_text = ResumeTailorer(llm=llm).tailor(
                profile, job_analysis, gap_report, conservative=conservative_mode
            )
    except RuntimeError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Resume tailoring failed: {exc}")
        return

    # --- Step 6: Optimize (iterative refinement, also calls LLM) ----------------
    try:
        with st.spinner("Optimizing tailored resume for alignment..."):
            optimization_result = ResumeTailoringOptimizer(llm=llm).optimize(
                profile, job_analysis, tailored_text, gap_report, conservative=conservative_mode
            )
    except RuntimeError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Optimization failed: {exc}")
        return

    # --- Step 7: Generate PDF -----------------------------------------------------
    try:
        with st.spinner("Generating PDF..."):
            pdf_path = PDFGenerator().generate(
                optimization_result.tailored_resume,
                profile.name,
                target_length=target_length,
                style_hints=style_hints,
            )
    except Exception as exc:
        st.error(f"PDF generation failed: {exc}")
        return

    # --- Step 8: Validate PDF (hard gate) -----------------------------------------
    try:
        with st.spinner("Validating generated PDF..."):
            # Resolve "preserve" to the concrete 1_page/2_page preset so the
            # validator enforces the same page limit generate() targeted.
            effective_length = PDFGenerator.resolve_target_length(target_length, style_hints)
            pdf_validation = PDFValidator().validate(pdf_path, target_length=effective_length)
    except Exception as exc:
        st.error(f"PDF validation failed: {exc}")
        return

    # --- Step 9: Build final report -----------------------------------------------
    try:
        report = ReportGenerator().generate_report(
            profile,
            job_analysis,
            benchmark,
            gap_report,
            optimization_result,
            pdf_validation,
        )
    except Exception as exc:
        st.error(f"Failed to build final report: {exc}")
        return

    # If the ONLY problem is that the content overflowed the 1-page target,
    # the PDF itself is still text-based and ATS-readable — treat it as a
    # recoverable "too long" case rather than a broken-PDF failure.
    page_count_issue_only = (
        not pdf_validation.passed
        and len(pdf_validation.issues) == 1
        and "page" in pdf_validation.issues[0].lower()
        and pdf_validation.page_count > 0
    )
    length_overflow_only = page_count_issue_only and effective_length == "1_page"

    # --- Display results ------------------------------------------------------------
    st.header("Results")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Original match score",
        f"{report['original_match_score']:.0%}",
    )
    col2.metric(
        "Tailored match score",
        f"{report['tailored_match_score']:.0%}",
        delta=f"{report['score_improvement']:+.0%}",
    )
    col3.metric(
        "Optimization iterations",
        report["optimization_iterations"],
    )

    if report["pdf_validation_passed"]:
        st.success("PDF validation passed: the generated resume is text-based and ATS-readable.")
    elif length_overflow_only:
        st.warning(
            "The PDF is text-based and ATS-readable, but it didn't fit the 1-page target."
        )
        for issue in report["pdf_validation_details"]["issues"]:
            st.write(f"- {issue}")
    else:
        st.error("PDF validation FAILED — do not send this resume as-is.")
        for issue in report["pdf_validation_details"]["issues"]:
            st.write(f"- {issue}")

    if report["optimization_ceiling_reached"] and report["tailored_match_score"] < 0.85:
        st.warning(
            "Optimization reached a plateau before hitting the 85% alignment target. "
            "See recommendations below."
        )

    st.subheader(f"Gaps addressed: {report['gaps_addressed_count']} / {report['total_gaps_count']}")

    with st.expander("Qualifications summary (by category A-E)"):
        for category_name, entries in report["qualifications_summary"].items():
            if not entries:
                continue
            st.markdown(f"**Category {category_name}**")
            for entry in entries:
                st.write(f"- {entry['requirement']} — {entry['reason']}")

    if report["recommendations"]:
        st.subheader("Recommendations")
        for rec in report["recommendations"]:
            st.write(f"- {rec}")

    st.subheader("Tailored resume text")
    st.text_area("Tailored resume", optimization_result.tailored_resume, height=400)

    # --- Resume Changes: side-by-side diff with reasoning ------------------------
    st.subheader("Resume Changes")
    try:
        diff_report = DiffGenerator().generate_diff(profile, optimization_result.tailored_resume)
    except Exception as exc:
        st.warning(f"Could not generate the resume change breakdown: {exc}")
        diff_report = None

    if diff_report is not None:
        col_orig, col_tail = st.columns(2)
        with col_orig:
            st.markdown("**Original bullets**")
            if diff_report.original_bullets:
                for bullet in diff_report.original_bullets:
                    st.write(f"- {bullet}")
            else:
                st.caption("No accomplishment bullets found in the original resume.")
        with col_tail:
            st.markdown("**Tailored bullets**")
            if diff_report.tailored_bullets:
                for bullet in diff_report.tailored_bullets:
                    st.write(f"- {bullet}")
            else:
                st.caption("No bullet points found in the tailored resume.")

        if diff_report.changes:
            with st.expander(f"What changed and why ({len(diff_report.changes)} change(s))"):
                for i, change in enumerate(diff_report.changes, start=1):
                    st.markdown(f"**{i}. {change.change_type.title()}**")
                    st.write(f"Reasoning: {change.reasoning}")
                    if change.original:
                        st.write(f"Original: {change.original}")
                    if change.tailored:
                        st.write(f"Tailored: {change.tailored}")
                    st.divider()
        else:
            st.caption("No bullet-level changes were detected.")

        if diff_report.issues:
            st.warning("Possible fabrication risks detected in the tailored resume:")
            for issue in diff_report.issues:
                st.write(f"- {issue}")

    if os.path.exists(pdf_path):
        if pdf_validation.passed:
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "Download tailored resume (PDF)",
                    data=f.read(),
                    file_name=f"{profile.name.replace(' ', '_')}_tailored_resume.pdf",
                    mime="application/pdf",
                )
        else:
            # Don't leave the user with nothing when the only problem is that
            # the content overflowed the 1-page target — offer the PDF with a
            # clear warning plus a concrete next step.
            if length_overflow_only:
                st.warning(
                    f"Your tailored resume needs {pdf_validation.page_count} pages to hold all "
                    "the content while staying readable — it doesn't fit on 1 page. "
                    "Try selecting **2 pages** or **Preserve original length** in the sidebar "
                    "and generating again. The PDF is still available below if you'd like to "
                    "review it as-is."
                )
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Download PDF anyway (exceeds 1-page target)",
                        data=f.read(),
                        file_name=f"{profile.name.replace(' ', '_')}_tailored_resume.pdf",
                        mime="application/pdf",
                    )


if __name__ == "__main__":
    main()
