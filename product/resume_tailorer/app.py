"""
Streamlit Web UI for the Resume Tailoring pipeline (Task 12).

Ties together the full pipeline built in Tasks 1-11:

    upload resume + job description
        -> ResumeParser.parse                (Task 2)
        -> JobAnalyzer.analyze                (Task 4)
        -> ResumeBenchmarker.benchmark        (Task 5)
        -> GapAnalyzer.analyze                (Task 6)
        -> ResumeTailorer.tailor              (Task 7, live Claude API call)
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
from pathlib import Path

import streamlit as st

from resume_tailorer.parsers import ResumeParser
from resume_tailorer.analyzers import JobAnalyzer, ResumeBenchmarker, GapAnalyzer
from resume_tailorer.tailorer import ResumeTailorer, ResumeTailoringOptimizer
from resume_tailorer.pdf import PDFGenerator, PDFValidator
from resume_tailorer.report_generator import ReportGenerator


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
        length_choice_ui = st.selectbox(
            "Target resume length",
            options=["1 page", "2 pages", "Preserve original length"],
            index=0,
        )
        target_length_map = {
            "1 page": "1_page",
            "2 pages": "2_page",
            "Preserve original length": "preserve",
        }
        target_length = target_length_map[length_choice_ui]

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

    # --- Step 1: Parse resume --------------------------------------------------
    resume_path = None
    try:
        with st.spinner("Parsing resume..."):
            resume_path = _save_uploaded_file(resume_file)
            parser = ResumeParser()
            profile = parser.parse(resume_path)

            # Extract the raw resume text so we can derive style hints
            # (bullet character, heading style) from the source formatting.
            # This mirrors the same extraction ResumeParser.parse() performs
            # internally, based on file extension.
            suffix = Path(resume_path).suffix.lower()
            if suffix == ".pdf":
                raw_resume_text = parser._extract_text_from_pdf(resume_path)
            elif suffix in (".docx", ".doc"):
                raw_resume_text = parser._extract_text_from_docx(resume_path)
            else:
                raw_resume_text = ""
            style_hints = parser.extract_style_hints(raw_resume_text)
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

    # --- Step 5: Tailor resume (live Claude API call) ---------------------------
    try:
        with st.spinner("Tailoring resume with Claude (this calls the live API)..."):
            tailored_text = ResumeTailorer().tailor(profile, job_analysis, gap_report)
    except Exception as exc:
        st.error(
            "Resume tailoring failed. This step calls the Anthropic Claude API "
            "and requires a valid ANTHROPIC_API_KEY in the environment. "
            f"Details: {exc}"
        )
        return

    # --- Step 6: Optimize (iterative refinement, also calls Claude) -------------
    try:
        with st.spinner("Optimizing tailored resume for alignment..."):
            optimization_result = ResumeTailoringOptimizer().optimize(
                profile, job_analysis, tailored_text, gap_report
            )
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
            pdf_validation = PDFValidator().validate(pdf_path, target_length=target_length)
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

    if pdf_validation.passed and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download tailored resume (PDF)",
                data=f.read(),
                file_name=f"{profile.name.replace(' ', '_')}_tailored_resume.pdf",
                mime="application/pdf",
            )


if __name__ == "__main__":
    main()
