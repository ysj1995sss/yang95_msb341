"""Shared orchestration for validated DOCX and PDF resume artifacts."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from resume_tailorer.artifacts.filenames import safe_artifact_filename
from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    FidelityMode,
    FindingSeverity,
    ResumeChange,
    ValidationStatus,
)
from resume_tailorer.docx_export.pipeline import run_docx_tailoring_pipeline
from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.pdf.validator import PDFValidator


_CORRECTABLE_FAILURES = frozenset({"PAGE_COUNT_CHANGED", "TEXT_OVERFLOW", "CLIPPED_TEXT"})


@dataclass(frozen=True)
class GeneratedArtifact:
    kind: str
    data: bytes
    filename: str
    mime_type: str


@dataclass(frozen=True)
class ArtifactPipelineRequest:
    original_resume_bytes: bytes
    original_filename: str
    profile: Any
    job_analysis: Any
    gap_report: Any
    company: str = ""
    role: str = ""
    job_snapshot: Mapping[str, Any] = field(default_factory=dict)
    candidate_fit: Mapping[str, Any] = field(default_factory=dict)
    tailored_text: str = ""
    target_length: str = "preserve"
    style_hints: Mapping[str, Any] = field(default_factory=dict)
    generate_pdf: bool = True
    changes: tuple[ResumeChange, ...] = ()


@dataclass(frozen=True)
class ArtifactAttemptResult:
    artifacts: tuple[GeneratedArtifact, ...]
    changes: tuple[ResumeChange, ...]
    validation: ArtifactValidation
    scoring_text: str


@dataclass(frozen=True)
class ArtifactPipelineResult:
    artifacts: tuple[GeneratedArtifact, ...]
    changes: tuple[ResumeChange, ...]
    validation: ArtifactValidation
    scoring_text: str
    fidelity_mode: FidelityMode
    attempt_count: int
    attempts: tuple[ArtifactAttemptResult, ...]

    @property
    def application_ready(self) -> bool:
        return self.validation.status is ValidationStatus.PASS


AttemptRunner = Callable[[ArtifactPipelineRequest], ArtifactAttemptResult]
CorrectionCallback = Callable[
    [ArtifactPipelineRequest, ArtifactAttemptResult], ArtifactPipelineRequest
]


class ValidatedArtifactPipeline:
    def __init__(
        self,
        docx_runner: AttemptRunner | None = None,
        pdf_runner: AttemptRunner | None = None,
        corrector: CorrectionCallback | None = None,
    ):
        self.docx_runner = docx_runner or self._run_docx
        self.pdf_runner = pdf_runner or self._run_pdf
        self.corrector = corrector

    def run(self, request: ArtifactPipelineRequest) -> ArtifactPipelineResult:
        suffix = Path(request.original_filename).suffix.lower()
        if suffix == ".docx":
            runner = self.docx_runner
            fidelity = FidelityMode.PRESERVED
        elif suffix == ".pdf":
            runner = self.pdf_runner
            fidelity = FidelityMode.RECONSTRUCTED
        else:
            raise ValueError(f"Unsupported resume type: {suffix or 'missing extension'}")

        first = runner(request)
        attempts = [first]
        if self.corrector is not None and self._is_correctable(first.validation):
            corrected_request = self.corrector(request, first)
            attempts.append(runner(corrected_request))

        final = attempts[-1]
        return ArtifactPipelineResult(
            artifacts=final.artifacts,
            changes=final.changes,
            validation=final.validation,
            scoring_text=final.scoring_text,
            fidelity_mode=fidelity,
            attempt_count=len(attempts),
            attempts=tuple(attempts),
        )
    @staticmethod
    def _is_correctable(validation: ArtifactValidation) -> bool:
        failures = {
            finding.code
            for finding in validation.findings
            if finding.severity is FindingSeverity.FAIL
        }
        return bool(failures) and failures <= _CORRECTABLE_FAILURES

    @staticmethod
    def _run_docx(request: ArtifactPipelineRequest) -> ArtifactAttemptResult:
        result = run_docx_tailoring_pipeline(
            request.original_resume_bytes,
            request.profile,
            request.job_analysis,
            request.gap_report,
            convert_to_pdf=request.generate_pdf,
        )
        artifacts = [
            GeneratedArtifact(
                "DOCX",
                result.docx_bytes,
                safe_artifact_filename(request.company, request.role, 1, "docx"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        ]
        if result.pdf_bytes:
            artifacts.append(
                GeneratedArtifact(
                    "PDF",
                    result.pdf_bytes,
                    safe_artifact_filename(request.company, request.role, 1, "pdf"),
                    "application/pdf",
                )
            )
        return ArtifactAttemptResult(
            artifacts=tuple(artifacts),
            changes=tuple(result.changes),
            validation=result.validation,
            scoring_text=result.tailored_scoring_text,
        )

    @staticmethod
    def _run_pdf(request: ArtifactPipelineRequest) -> ArtifactAttemptResult:
        if not request.tailored_text.strip():
            raise ValueError("tailored_text is required for a PDF-only original")
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "tailored.pdf")
            PDFGenerator().generate(
                request.tailored_text,
                request.profile.name,
                output_path=output_path,
                target_length=request.target_length,
                style_hints=dict(request.style_hints),
            )
            expected_pages = (request.style_hints or {}).get("page_count")
            validation = PDFValidator().validate_artifact(
                output_path,
                profile=request.profile,
                expected_page_count=expected_pages,
                accepted_changes=list(request.changes),
            )
            with open(output_path, "rb") as artifact_file:
                pdf_bytes = artifact_file.read()
        return ArtifactAttemptResult(
            artifacts=(
                GeneratedArtifact(
                    "PDF",
                    pdf_bytes,
                    safe_artifact_filename(request.company, request.role, 1, "pdf"),
                    "application/pdf",
                ),
            ),
            changes=request.changes,
            validation=validation,
            scoring_text=request.tailored_text,
        )
