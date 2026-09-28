"""Validated resume artifact domain."""

from .filenames import safe_artifact_filename
from .models import (
    ArtifactMetadata,
    ArtifactValidation,
    ChangeCategory,
    ChangeDisposition,
    FidelityMode,
    FinalApplicationReport,
    FindingCategory,
    FindingSeverity,
    ResumeChange,
    ValidationFinding,
    ValidationStatus,
)
from .changes import build_freeform_changes
from .report import build_final_report

__all__ = [
    "ArtifactMetadata",
    "ArtifactValidation",
    "ChangeCategory",
    "ChangeDisposition",
    "FidelityMode",
    "FinalApplicationReport",
    "FindingCategory",
    "FindingSeverity",
    "ResumeChange",
    "ValidationFinding",
    "ValidationStatus",
    "safe_artifact_filename",
    "build_final_report",
    "build_freeform_changes",
]
