"""Shared immutable models for resume artifact generation and review."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ValidationStatus(_StringEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class FindingSeverity(_StringEnum):
    WARNING = "WARNING"
    FAIL = "FAIL"


class FindingCategory(_StringEnum):
    STRUCTURE = "STRUCTURE"
    CONTENT = "CONTENT"
    TRUTH = "TRUTH"
    VISUAL = "VISUAL"
    ATS = "ATS"
    CONVERSION = "CONVERSION"


class FidelityMode(_StringEnum):
    PRESERVED = "PRESERVED"
    RECONSTRUCTED = "RECONSTRUCTED"


class ChangeCategory(_StringEnum):
    REPHRASED = "REPHRASED"
    REORDERED = "REORDERED"
    CONDENSED = "CONDENSED"
    COMPETENCY_CHANGED = "COMPETENCY_CHANGED"
    UNCHANGED = "UNCHANGED"
    REJECTED = "REJECTED"


class ChangeDisposition(_StringEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    RESTORED = "RESTORED"
    MANUALLY_EDITED = "MANUALLY_EDITED"


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    severity: FindingSeverity
    category: FindingCategory
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactValidation:
    status: ValidationStatus
    findings: tuple[ValidationFinding, ...] = ()
    original_page_count: int | None = None
    tailored_page_count: int | None = None
    extracted_text: str = ""
    checks_run: tuple[str, ...] = ()

    @classmethod
    def from_findings(
        cls,
        findings: list[ValidationFinding] | tuple[ValidationFinding, ...],
        **values: Any,
    ) -> "ArtifactValidation":
        immutable_findings = tuple(findings)
        if any(item.severity is FindingSeverity.FAIL for item in immutable_findings):
            status = ValidationStatus.FAIL
        elif immutable_findings:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.PASS
        return cls(status=status, findings=immutable_findings, **values)

    def has_code(self, code: str) -> bool:
        return any(item.code == code for item in self.findings)


@dataclass(frozen=True)
class ResumeChange:
    change_id: str
    section: str
    source_index: int | None
    original_text: str
    proposed_text: str
    category: ChangeCategory
    reason: str
    job_requirement: str
    evidence_source: str
    evidence_text: str
    validation_status: ValidationStatus
    disposition: ChangeDisposition = ChangeDisposition.PENDING


@dataclass(frozen=True)
class ArtifactMetadata:
    artifact_id: str
    run_id: str
    version: int
    kind: str
    filename: str
    mime_type: str
    sha256: str
    size_bytes: int
    created_at: datetime
    validation_status: ValidationStatus


@dataclass(frozen=True)
class FinalApplicationReport:
    company: str
    role: str
    candidate_fit: float | None
    fit_breakdown: Mapping[str, Any]
    original_alignment: float
    tailored_alignment: float
    strong_matches: tuple[str, ...]
    partial_matches: tuple[str, ...]
    true_gaps: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    validation: ArtifactValidation
    fidelity_mode: FidelityMode
    original_page_count: int | None
    tailored_page_count: int | None
    artifacts: tuple[ArtifactMetadata, ...] = ()

