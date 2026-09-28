from dataclasses import replace

from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    FidelityMode,
    FindingCategory,
    FindingSeverity,
    ValidationFinding,
    ValidationStatus,
)
from resume_tailorer.artifacts.pipeline import (
    ArtifactAttemptResult,
    ArtifactPipelineRequest,
    GeneratedArtifact,
    ValidatedArtifactPipeline,
)
from resume_tailorer.models import CareerTruthProfile


def _profile():
    return CareerTruthProfile(
        contact_info={}, education=[], work_experience=[], skills=[], tools=[],
        certifications=[], accomplishments=[]
    )


def _request(filename="resume.pdf"):
    return ArtifactPipelineRequest(
        original_resume_bytes=b"original",
        original_filename=filename,
        profile=_profile(),
        job_analysis=JobAnalyzer().analyze("Analyst role requiring communication."),
        gap_report=GapReport(items=[], summary="No gaps"),
        company="Example Corp",
        role="Analyst",
        tailored_text="Tailored text",
        generate_pdf=True,
    )


def _validation(code=None):
    if code is None:
        return ArtifactValidation.from_findings([])
    category = FindingCategory.TRUTH if code == "UNSUPPORTED_CLAIM" else FindingCategory.VISUAL
    return ArtifactValidation.from_findings([
        ValidationFinding(code, FindingSeverity.FAIL, category, code.replace("_", " "))
    ])


def _attempt(validation):
    return ArtifactAttemptResult(
        artifacts=(GeneratedArtifact("PDF", b"pdf", "resume.pdf", "application/pdf"),),
        changes=(),
        validation=validation,
        scoring_text="Tailored text",
    )


class RecordingRunner:
    def __init__(self, validations):
        self.validations = list(validations)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return _attempt(self.validations.pop(0))


class RecordingCorrector:
    def __init__(self):
        self.calls = []

    def __call__(self, request, result):
        self.calls.append((request, result))
        return replace(request, tailored_text="Condensed verified text")


def test_docx_dispatch_uses_master_template():
    docx_runner = RecordingRunner([_validation()])
    pdf_runner = RecordingRunner([_validation()])
    result = ValidatedArtifactPipeline(
        docx_runner=docx_runner, pdf_runner=pdf_runner
    ).run(_request("resume.docx"))
    assert len(docx_runner.requests) == 1
    assert pdf_runner.requests == []
    assert result.fidelity_mode is FidelityMode.PRESERVED
    assert result.application_ready is True


def test_pdf_dispatch_is_labeled_reconstructed():
    result = ValidatedArtifactPipeline(
        docx_runner=RecordingRunner([_validation()]),
        pdf_runner=RecordingRunner([_validation()]),
    ).run(_request("resume.pdf"))
    assert result.fidelity_mode is FidelityMode.RECONSTRUCTED


def test_overflow_gets_exactly_one_correction():
    runner = RecordingRunner([_validation("PAGE_COUNT_CHANGED"), _validation()])
    corrector = RecordingCorrector()
    result = ValidatedArtifactPipeline(
        docx_runner=runner, pdf_runner=runner, corrector=corrector
    ).run(_request())
    assert len(corrector.calls) == 1
    assert result.attempt_count == 2
    assert result.validation.status is ValidationStatus.PASS
    assert runner.requests[1].original_resume_bytes == b"original"


def test_second_overflow_failure_is_not_retried_again():
    runner = RecordingRunner([
        _validation("TEXT_OVERFLOW"), _validation("CLIPPED_TEXT")
    ])
    corrector = RecordingCorrector()
    result = ValidatedArtifactPipeline(
        docx_runner=runner, pdf_runner=runner, corrector=corrector
    ).run(_request())
    assert len(corrector.calls) == 1
    assert result.attempt_count == 2
    assert result.validation.status is ValidationStatus.FAIL


def test_truth_failure_is_never_retried():
    runner = RecordingRunner([_validation("UNSUPPORTED_CLAIM")])
    corrector = RecordingCorrector()
    result = ValidatedArtifactPipeline(
        docx_runner=runner, pdf_runner=runner, corrector=corrector
    ).run(_request())
    assert corrector.calls == []
    assert result.validation.status is ValidationStatus.FAIL
    assert result.application_ready is False


def test_warning_artifact_is_reviewable_but_not_application_ready():
    warning = ArtifactValidation.from_findings([
        ValidationFinding("VISUAL_CHECK_SKIPPED", FindingSeverity.WARNING,
                          FindingCategory.VISUAL, "Skipped")
    ])
    result = ValidatedArtifactPipeline(
        docx_runner=RecordingRunner([warning]), pdf_runner=RecordingRunner([warning])
    ).run(_request())
    assert result.artifacts
    assert result.application_ready is False
