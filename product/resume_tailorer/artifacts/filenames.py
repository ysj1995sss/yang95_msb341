"""Deterministic, filesystem-safe names for tailored resume artifacts."""

import re


_SAFE_EXTENSION = re.compile(r"^[A-Za-z0-9]+$")


def _sanitize_component(value: str, fallback: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip()).strip("_")
    return sanitized or fallback


def safe_artifact_filename(
    company: str,
    role: str,
    version: int,
    extension: str,
) -> str:
    if version < 1:
        raise ValueError("artifact version must be positive")

    normalized_extension = (extension or "").lstrip(".")
    if not _SAFE_EXTENSION.fullmatch(normalized_extension):
        raise ValueError("extension must contain only letters and numbers")

    safe_company = _sanitize_component(company, "Target")
    safe_role = _sanitize_component(role, "Job")
    return (
        f"{safe_company}_{safe_role}_Tailored_Resume_v{version}."
        f"{normalized_extension.lower()}"
    )

