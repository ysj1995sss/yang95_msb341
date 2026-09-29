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
