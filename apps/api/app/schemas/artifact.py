"""API-facing shapes for tailoring runs and artifacts (Steps 16-20).

Mirrors product/resume_tailorer/artifacts/models.py's enums as plain
strings (Pydantic validates against the same literal values) rather than
importing the product-layer enum classes directly into the API schema
layer -- matches how GapItemOut/BulletChangeOut already re-declare their
own fields instead of importing resume_tailorer dataclasses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ValidationFindingOut(BaseModel):
    code: str
    severity: str
    category: str
    message: str
    details: dict = Field(default_factory=dict)


class ArtifactValidationOut(BaseModel):
    status: str
    findings: list[ValidationFindingOut] = Field(default_factory=list)
    original_page_count: int | None = None
    tailored_page_count: int | None = None


class ResumeChangeOut(BaseModel):
    change_id: str
    section: str
    source_index: int | None
    original_text: str
    proposed_text: str
    category: str
    reason: str
    job_requirement: str
    evidence_source: str
    evidence_text: str
    validation_status: str
    disposition: str
    manual_text: str | None = None


class ArtifactMetadataOut(BaseModel):
    artifact_id: str
    run_id: str
    version: int
    kind: str
    filename: str
    mime_type: str
    sha256: str
    size_bytes: int
    created_at: datetime
    validation_status: str


class FinalApplicationReportOut(BaseModel):
    company: str
    role: str
    candidate_fit: float | None
    fit_breakdown: dict
    original_alignment: float
    tailored_alignment: float
    strong_matches: list[str] = Field(default_factory=list)
    partial_matches: list[str] = Field(default_factory=list)
    true_gaps: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    validation: ArtifactValidationOut
    fidelity_mode: str
    original_page_count: int | None
    tailored_page_count: int | None
    artifacts: list[ArtifactMetadataOut] = Field(default_factory=list)


class TailoringRunOut(BaseModel):
    run_id: str
    state: str
    report: FinalApplicationReportOut
    changes: list[ResumeChangeOut] = Field(default_factory=list)
    validation: ArtifactValidationOut
    artifacts: list[ArtifactMetadataOut] = Field(default_factory=list)


class ChangeDispositionIn(BaseModel):
    change_id: str
    disposition: str
    manual_text: str | None = None


class ReviewChangesRequest(BaseModel):
    changes: list[ChangeDispositionIn]
