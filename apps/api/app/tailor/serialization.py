"""JSON (de)serialization between product-layer artifact dataclasses and
the canonical-JSON text columns TailoringRunStore persists. Kept separate
from router.py so the orchestration logic isn't buried under conversion
code -- the enums in resume_tailorer.artifacts.models all subclass `str`,
so `dataclasses.asdict()` already produces JSON-serializable values for
them; this module only has to handle the round trip back INTO dataclasses,
which `asdict()` cannot do.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    ChangeCategory,
    ChangeDisposition,
    FindingCategory,
    FindingSeverity,
    ResumeChange,
    ValidationFinding,
    ValidationStatus,
)


def profile_snapshot_hash(profile_dict: dict) -> str:
    canonical = json.dumps(profile_dict, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def changes_to_json(changes: list[ResumeChange] | tuple[ResumeChange, ...]) -> list[dict]:
    return [asdict(change) for change in changes]


def changes_from_json(data: list[dict]) -> list[ResumeChange]:
    return [
        ResumeChange(
            change_id=item["change_id"],
            section=item["section"],
            source_index=item["source_index"],
            original_text=item["original_text"],
            proposed_text=item["proposed_text"],
            category=ChangeCategory(item["category"]),
            reason=item["reason"],
            job_requirement=item["job_requirement"],
            evidence_source=item["evidence_source"],
            evidence_text=item["evidence_text"],
            validation_status=ValidationStatus(item["validation_status"]),
            disposition=ChangeDisposition(item["disposition"]),
        )
        for item in data
    ]


def validation_to_json(validation: ArtifactValidation) -> dict:
    return asdict(validation)


def validation_from_json(data: dict) -> ArtifactValidation:
    findings = [
        ValidationFinding(
            code=item["code"],
            severity=FindingSeverity(item["severity"]),
            category=FindingCategory(item["category"]),
            message=item["message"],
            details=item.get("details", {}),
        )
        for item in data.get("findings", [])
    ]
    return ArtifactValidation(
        status=ValidationStatus(data["status"]),
        findings=tuple(findings),
        original_page_count=data.get("original_page_count"),
        tailored_page_count=data.get("tailored_page_count"),
        extracted_text=data.get("extracted_text", ""),
        checks_run=tuple(data.get("checks_run", ())),
    )


def report_to_json(report: Any) -> dict:
    """`report` is a FinalApplicationReport; asdict() handles the nested
    ArtifactValidation/ArtifactMetadata dataclasses recursively."""
    return asdict(report)
