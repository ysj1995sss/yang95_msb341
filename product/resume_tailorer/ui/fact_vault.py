"""Pure view model for the Fact Vault workspace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class FactVaultSummary:
    has_profile: bool
    skill_count: int
    bullet_count: int
    resume_fact_count: int
    user_edit_count: int
    unresolved_count: int
    next_action: str


def build_fact_vault_summary(
    profile: Mapping[str, Any] | None,
    verification: Mapping[str, str] | None,
) -> FactVaultSummary:
    profile = profile or {}
    verification = verification or {}
    jobs = profile.get("work_experience") or []
    bullet_count = sum(
        len(job.get("responsibilities") or []) + len(job.get("accomplishments") or [])
        for job in jobs
    )
    skill_count = len(profile.get("skills") or [])
    resume_fact_count = (
        skill_count
        + len(profile.get("tools") or [])
        + len(profile.get("certifications") or [])
        + len(profile.get("education") or [])
        + bullet_count
    )
    user_edit_count = sum(value == "user_verified" for value in verification.values())
    unresolved_count = sum(value in {"unverified", "needs_review"} for value in verification.values())
    has_profile = bool(resume_fact_count or profile.get("contact_info") or jobs)
    return FactVaultSummary(
        has_profile=has_profile,
        skill_count=skill_count,
        bullet_count=bullet_count,
        resume_fact_count=resume_fact_count,
        user_edit_count=user_edit_count,
        unresolved_count=unresolved_count,
        next_action=(
            "Review unresolved facts before tailoring."
            if unresolved_count
            else "Your verified facts are ready for job matching."
            if has_profile
            else "Upload a resume to build your Fact Vault."
        ),
    )


@dataclass(frozen=True)
class SectionCompleteness:
    name: str
    percent: int | None  # None = optional section with nothing to complete
    missing: tuple[str, ...]


def _section(name: str, checks: list[tuple[str, bool]]) -> SectionCompleteness:
    missing = tuple(label for label, ok in checks if not ok)
    return SectionCompleteness(name, round(100 * (len(checks) - len(missing)) / len(checks)), missing)


def build_section_completeness(profile: Mapping[str, Any] | None) -> tuple[SectionCompleteness, ...]:
    """Per-section completeness from fields actually present; never invents a value."""
    profile = profile or {}
    contact = profile.get("contact_info") or {}
    jobs = profile.get("work_experience") or []
    edu = profile.get("education") or []

    experience_checks: list[tuple[str, bool]] = []
    for i, job in enumerate(jobs, start=1):
        who = job.get("title") or f"Role {i}"
        experience_checks.append((f"{who}: dates", bool((job.get("dates") or "").strip())))
        experience_checks.append(
            (f"{who}: at least one bullet", bool(job.get("responsibilities") or job.get("accomplishments")))
        )
    if not experience_checks:
        experience_checks = [("At least one job", False)]

    education_checks: list[tuple[str, bool]] = []
    for i, entry in enumerate(edu, start=1):
        who = entry.get("institution") or f"Education {i}"
        education_checks.append((f"{who}: degree", bool((entry.get("degree") or "").strip())))
        education_checks.append((f"{who}: year", bool(entry.get("year"))))
    if not education_checks:
        education_checks = [("At least one degree", False)]

    certs = profile.get("certifications") or []
    return (
        _section("Contact", [(k.capitalize(), bool((contact.get(k) or "").strip())) for k in ("name", "email", "phone", "location")]),
        _section("Experience", experience_checks),
        _section("Education", education_checks),
        _section("Skills", [("Skills", bool(profile.get("skills"))), ("Tools", bool(profile.get("tools")))]),
        SectionCompleteness("Certifications", 100 if certs else None, ()),
    )


def overall_completeness(sections: tuple[SectionCompleteness, ...]) -> int:
    scored = [s.percent for s in sections if s.percent is not None]
    return round(sum(scored) / len(scored)) if scored else 0
