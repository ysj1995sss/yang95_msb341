"""Deterministic content checks for generated resume PDFs."""

from __future__ import annotations

import re
import unicodedata

from resume_tailorer.artifacts.models import (
    ChangeDisposition,
    FindingCategory,
    FindingSeverity,
    ResumeChange,
    ValidationFinding,
)
from resume_tailorer.models import CareerTruthProfile


_METRIC_RE = re.compile(r"\$?\d[\d,.]*\s*(?:%|k|m|b|x|×|\+|-person|-year|s\b)?", re.I)
_PLACEHOLDER_RE = re.compile(
    r"\[(?:insert|add|fill|replace)[^\]]*\]|\b(?:lorem ipsum|your name here)\b",
    re.I,
)
_COMMENTARY_RE = re.compile(r"\b(?:as an ai|here is (?:the|your) (?:revised|tailored) resume)\b", re.I)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    return re.sub(r"\s+", " ", value).strip()


def _contains(text: str, expected: str) -> bool:
    return bool(expected and _normalize(expected) in _normalize(text))


def _failure(code: str, category: FindingCategory, message: str, **details) -> ValidationFinding:
    return ValidationFinding(code, FindingSeverity.FAIL, category, message, details)


def validate_pdf_content(
    extracted_text: str,
    profile: CareerTruthProfile,
    accepted_changes: list[ResumeChange],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    text = extracted_text or ""

    contact_values = [
        str(value).strip()
        for value in profile.contact_info.values()
        if value is not None and str(value).strip()
    ]
    missing_contact = [value for value in contact_values if not _contains(text, value)]
    if missing_contact:
        findings.append(
            _failure(
                "CONTACT_MISSING",
                FindingCategory.CONTENT,
                "One or more contact identifiers are missing from the generated PDF.",
                missing=missing_contact,
            )
        )

    for job in profile.work_experience:
        if job.employer and not _contains(text, job.employer):
            findings.append(_failure("EMPLOYER_MISSING", FindingCategory.CONTENT,
                                     f"Employer is missing: {job.employer}", employer=job.employer))
        if job.dates and not _contains(text, job.dates):
            findings.append(_failure("JOB_DATE_MISSING", FindingCategory.CONTENT,
                                     f"Job dates are missing: {job.dates}", dates=job.dates))
        if job.location and not _contains(text, job.location):
            findings.append(_failure("LOCATION_MISSING", FindingCategory.CONTENT,
                                     f"Job location is missing: {job.location}", location=job.location))

    for education in profile.education:
        if education.institution and not _contains(text, education.institution):
            findings.append(_failure("EDUCATION_MISSING", FindingCategory.CONTENT,
                                     f"Education entry is missing: {education.institution}"))
        if education.year and not _contains(text, str(education.year)):
            findings.append(_failure("EDUCATION_DATE_MISSING", FindingCategory.CONTENT,
                                     f"Education date is missing: {education.year}"))

    source_text = " ".join(
        value
        for job in profile.work_experience
        for value in [*job.responsibilities, *job.accomplishments]
    )
    expected_metrics = {match.group().strip() for match in _METRIC_RE.finditer(source_text)}
    missing_metrics = sorted(metric for metric in expected_metrics if metric not in text)
    if missing_metrics:
        findings.append(_failure("METRIC_MISSING", FindingCategory.TRUTH,
                                 "Verified metrics are missing from the generated PDF.",
                                 missing=missing_metrics))

    for change in accepted_changes:
        if change.disposition in (ChangeDisposition.REJECTED, ChangeDisposition.RESTORED):
            expected = change.original_text
        else:
            expected = change.proposed_text
        if expected and not _contains(text, expected):
            findings.append(_failure("ACCEPTED_CHANGE_MISSING", FindingCategory.CONTENT,
                                     "Reviewed change text is missing from the generated PDF.",
                                     change_id=change.change_id))

    bullets = [
        _normalize(re.sub(r"^[-*•]\s*", "", line.strip()))
        for line in text.splitlines()
        if re.match(r"^\s*[-*•]\s+", line)
    ]
    duplicates = sorted({bullet for bullet in bullets if bullet and bullets.count(bullet) > 1})
    if duplicates:
        findings.append(_failure("DUPLICATE_BULLET", FindingCategory.CONTENT,
                                 "The generated PDF contains duplicated bullets.",
                                 duplicates=duplicates))

    if _PLACEHOLDER_RE.search(text):
        findings.append(_failure("PLACEHOLDER_TEXT", FindingCategory.CONTENT,
                                 "The generated PDF contains unfinished placeholder text."))
    if _COMMENTARY_RE.search(text):
        findings.append(_failure("LLM_COMMENTARY", FindingCategory.CONTENT,
                                 "The generated PDF contains model commentary."))
    if any(line.rstrip().endswith(("...", "…")) for line in text.splitlines()):
        findings.append(_failure("TRUNCATED_TEXT", FindingCategory.CONTENT,
                                 "A line appears truncated in the generated PDF."))
    return findings
