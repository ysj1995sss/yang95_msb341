"""
Task 9 (spec 002, Steps 16-20): acceptance tests against real, anonymized
resume fixtures for the validated artifact pipeline.

No live LLM call is made here -- a deterministic stand-in bullet
tailorer/tailored text plays the same role test_integration.py's
TestMockedEndToEndPipeline gives a MagicMock LLMClient, for the same
reason: no provider API key is configured in this environment, and these
tests must run in CI/sandboxes without network access or API cost. A
one-off LIVE run (using a configured LLM if local keys are present) was
performed manually per the sprint plan's Task 9 Step 4 and its results
are recorded in HANDOFF-TO-CODEX.md and decisions/015, not committed as
a network-dependent pytest test.

Word/docx2pdf is not installed in this environment (see
HANDOFF-TO-CODEX.md), so the DOCX->PDF conversion step cannot run live
here either; the DOCX acceptance tests instead assert the documented
graceful-degradation behavior (docx_bytes still produced,
conversion_available=False) rather than skipping page-count checks
outright.

"Immutable artifact lineage" (supersedes_artifact_id chains, version
numbering) is a persistence-layer guarantee exercised end-to-end in
apps/api/tests/test_tailoring_artifact_storage.py; what this file
verifies at the product layer is the invariant that guarantee depends
on -- every regeneration rebuilds from the untouched original baseline,
never from a prior regeneration's output (see
test_regeneration_is_idempotent_regardless_of_history below).
"""

from __future__ import annotations

import io
from dataclasses import replace
from pathlib import Path

import pytest
from docx import Document

from resume_tailorer.analyzers import GapAnalyzer, JobAnalyzer, ResumeBenchmarker
from resume_tailorer.analyzers.gap_analyzer import find_unsupported_claims
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import ChangeDisposition, FidelityMode
from resume_tailorer.artifacts.regeneration import regenerate_docx_artifact
from resume_tailorer.artifacts.report import build_final_report
from resume_tailorer.docx_export import pipeline as pipeline_module
from resume_tailorer.docx_export.converter import DocxConversionUnavailable
from resume_tailorer.docx_export.pipeline import run_docx_tailoring_pipeline
from resume_tailorer.parsers.resume_parser import ResumeParser
from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.tailorer.docx_bullet_tailorer import BulletEdit, BulletTailoringResult

from tests.fixtures.real_job_descriptions import JOB_DESCRIPTIONS

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "artifacts"
DOCX_RESUME_PATH = FIXTURES_DIR / "sample_docx_resume.docx"
PDF_RESUME_PATH = FIXTURES_DIR / "sample_pdf_only_resume.pdf"


class _EchoBulletTailorer:
    """Deterministic stand-in for DocxBulletTailorer: appends a keyword
    already backed by the job posting to each bullet that doesn't already
    mention it, so every acceptance run produces the same, verifiable
    (non-fabricated) edits without a live LLM call."""

    def __init__(self, keyword: str):
        self._keyword = keyword

    def tailor_bullets(self, bullets, profile, job_analysis, gap_report, max_repair_attempts=1, priority_focus=None):
        edits = []
        for b in bullets:
            if self._keyword.lower() in b.text.lower():
                edits.append(BulletEdit(b.paragraph_index, b.text, b.text, changed=False))
            else:
                edits.append(BulletEdit(b.paragraph_index, b.text, f"{b.text} using {self._keyword}", changed=True))
        return BulletTailoringResult(edits=edits, warnings=[])


@pytest.fixture(scope="module")
def docx_profile():
    return ResumeParser().parse(str(DOCX_RESUME_PATH))


@pytest.fixture(scope="module")
def backend_job_analysis():
    return JobAnalyzer().analyze(JOB_DESCRIPTIONS[0])


@pytest.fixture(scope="module")
def docx_gap_report(docx_profile, backend_job_analysis):
    benchmark = ResumeBenchmarker().benchmark(docx_profile, backend_job_analysis)
    return GapAnalyzer().analyze(docx_profile, backend_job_analysis, benchmark)


class TestDocxAcceptance:
    def test_all_jobs_education_contact_and_metrics_survive_tailoring(
        self, docx_profile, backend_job_analysis, docx_gap_report
    ):
        original_bytes = DOCX_RESUME_PATH.read_bytes()
        result = run_docx_tailoring_pipeline(
            original_bytes, docx_profile, backend_job_analysis, docx_gap_report,
            bullet_tailorer=_EchoBulletTailorer("Kubernetes"), convert_to_pdf=False,
        )

        text = result.tailored_scoring_text
        assert "Northwind Analytics" in text and "Beacon Software Co." in text
        assert "State University" in text
        # Metrics carried over from the original bullets verbatim.
        assert "35%" in text and "60%" in text
        assert find_unsupported_claims(docx_gap_report, text) == []

        # Contact info isn't part of the synthesized scoring text (that
        # text is for keyword scoring only) -- the splice must still leave
        # the untouched header paragraph exactly as it was in the DOCX
        # bytes themselves.
        spliced_text = "\n".join(p.text for p in Document(io.BytesIO(result.docx_bytes)).paragraphs)
        assert "alex.rivera.demo@example.com" in spliced_text

    def test_docx_bytes_and_graceful_degradation_when_word_is_unavailable(
        self, docx_profile, backend_job_analysis, docx_gap_report, monkeypatch
    ):
        def fake_convert(src, dst):
            raise DocxConversionUnavailable("Word not installed in this environment")

        monkeypatch.setattr(pipeline_module, "convert_docx_to_pdf", fake_convert)
        original_bytes = DOCX_RESUME_PATH.read_bytes()

        result = run_docx_tailoring_pipeline(
            original_bytes, docx_profile, backend_job_analysis, docx_gap_report,
            bullet_tailorer=_EchoBulletTailorer("Kubernetes"), convert_to_pdf=True,
        )
        assert result.docx_bytes  # splicing never depends on conversion succeeding
        assert result.conversion_available is False
        assert result.pdf_bytes is None
        assert result.original_page_count is None
        assert result.tailored_page_count is None

    def test_rejected_change_regenerates_the_untouched_original_bullet(
        self, docx_profile, backend_job_analysis, docx_gap_report
    ):
        original_bytes = DOCX_RESUME_PATH.read_bytes()
        first = run_docx_tailoring_pipeline(
            original_bytes, docx_profile, backend_job_analysis, docx_gap_report,
            bullet_tailorer=_EchoBulletTailorer("Kubernetes"), convert_to_pdf=False,
        )
        assert first.changes, "fixture must produce at least one reviewable change"

        rejected = [replace(c, disposition=ChangeDisposition.REJECTED) for c in first.changes]
        regenerated = regenerate_docx_artifact(
            original_docx_bytes=original_bytes, changes=rejected,
            profile=docx_profile, gap_report=docx_gap_report, convert_to_pdf=False,
        )
        spliced_text = "\n".join(p.text for p in Document(io.BytesIO(regenerated.docx_bytes)).paragraphs)
        for change in first.changes:
            assert change.proposed_text not in spliced_text
            assert change.original_text in spliced_text

    def test_manually_edited_text_survives_regeneration_exactly(
        self, docx_profile, backend_job_analysis, docx_gap_report
    ):
        original_bytes = DOCX_RESUME_PATH.read_bytes()
        first = run_docx_tailoring_pipeline(
            original_bytes, docx_profile, backend_job_analysis, docx_gap_report,
            bullet_tailorer=_EchoBulletTailorer("Kubernetes"), convert_to_pdf=False,
        )
        target = first.changes[0]
        manual_text = f"{target.original_text} (manually reviewed and approved)"
        edited = [
            replace(c, disposition=ChangeDisposition.MANUALLY_EDITED, proposed_text=manual_text)
            if c.change_id == target.change_id else c
            for c in first.changes
        ]
        regenerated = regenerate_docx_artifact(
            original_docx_bytes=original_bytes, changes=edited,
            profile=docx_profile, gap_report=docx_gap_report, convert_to_pdf=False,
        )
        spliced_text = "\n".join(p.text for p in Document(io.BytesIO(regenerated.docx_bytes)).paragraphs)
        assert manual_text in spliced_text

    def test_regeneration_is_idempotent_regardless_of_history(
        self, docx_profile, backend_job_analysis, docx_gap_report
    ):
        """Immutable artifact lineage (each version created from the
        untouched original) depends on this: regenerating twice from the
        same disposition set must be byte-identical, whether or not a
        DIFFERENT disposition was regenerated in between."""
        original_bytes = DOCX_RESUME_PATH.read_bytes()
        first = run_docx_tailoring_pipeline(
            original_bytes, docx_profile, backend_job_analysis, docx_gap_report,
            bullet_tailorer=_EchoBulletTailorer("Kubernetes"), convert_to_pdf=False,
        )
        rejected = [replace(c, disposition=ChangeDisposition.REJECTED) for c in first.changes]
        accepted = [replace(c, disposition=ChangeDisposition.ACCEPTED) for c in first.changes]

        run_a = regenerate_docx_artifact(
            original_docx_bytes=original_bytes, changes=rejected,
            profile=docx_profile, gap_report=docx_gap_report, convert_to_pdf=False,
        )
        # Regenerate with a DIFFERENT disposition set in between.
        regenerate_docx_artifact(
            original_docx_bytes=original_bytes, changes=accepted,
            profile=docx_profile, gap_report=docx_gap_report, convert_to_pdf=False,
        )
        run_b = regenerate_docx_artifact(
            original_docx_bytes=original_bytes, changes=rejected,
            profile=docx_profile, gap_report=docx_gap_report, convert_to_pdf=False,
        )
        # Compare rendered paragraph text rather than raw zip bytes -- a
        # DOCX's zip container embeds a fresh save timestamp every write,
        # so two content-identical saves are never byte-identical.
        text_a = [p.text for p in Document(io.BytesIO(run_a.docx_bytes)).paragraphs]
        text_b = [p.text for p in Document(io.BytesIO(run_b.docx_bytes)).paragraphs]
        assert text_a == text_b


class TestPdfOnlyAcceptance:
    def test_pdf_only_upload_is_labeled_reconstructed_with_a_validated_report(self, tmp_path):
        profile = ResumeParser().parse(str(PDF_RESUME_PATH))
        job_analysis = JobAnalyzer().analyze(JOB_DESCRIPTIONS[1])
        benchmark = ResumeBenchmarker().benchmark(profile, job_analysis)
        gap_report = GapAnalyzer().analyze(profile, job_analysis, benchmark)

        # No LLM configured in this environment -- a hand-written tailored
        # text stands in for ResumeTailoringOptimizer's output (same
        # precedent as test_integration.py's mocked end-to-end test).
        tailored_text = (
            "Jordan Lee\n"
            "jordan.lee.demo@example.com | (555) 020-0200 | Rivertown, ST\n\n"
            "WORK EXPERIENCE\n"
            "Data Analyst\n"
            "Fernbridge Retail Group | Remote | 2020-2024\n"
            "- Built a demand-forecasting model in Python that reduced stockouts by 22%\n"
            "- Automated weekly reporting, saving the team 10 hours per week\n"
            "Junior Data Analyst\n"
            "Lakeview Consulting | Remote | 2018-2020\n"
            "- Built dashboards in Tableau used by 30+ stakeholders weekly\n\n"
            "EDUCATION\n"
            "B.A. in Economics, Lakeview State University, 2018\n\n"
            "SKILLS\n"
            "SQL, Python, Tableau, Excel, pandas, A/B testing\n"
        )
        changes = build_freeform_changes(profile, tailored_text, gap_report)
        unsupported = find_unsupported_claims(gap_report, tailored_text)
        assert unsupported == []

        pdf_path = str(tmp_path / "jordan_lee_tailored.pdf")
        PDFGenerator().generate(tailored_text, profile.name, output_path=pdf_path, target_length="preserve")
        validation = PDFValidator().validate_artifact(
            pdf_path, profile=profile, expected_page_count=None, accepted_changes=changes,
        )

        report = build_final_report(
            candidate_fit=None,
            fit_breakdown={},
            original_alignment=benchmark.original_match_score,
            tailored_alignment=benchmark.original_match_score,
            gap_report=gap_report,
            validation=validation,
            fidelity_mode=FidelityMode.RECONSTRUCTED,
            unsupported_claims=unsupported,
        )
        assert report.fidelity_mode is FidelityMode.RECONSTRUCTED
        assert report.unsupported_claims == ()
        assert report.validation.status is not None
