"""Convert freeform resume diffs into evidence-linked shared changes."""

from __future__ import annotations

import re
from dataclasses import replace

from resume_tailorer.analyzers.gap_analyzer import GapItem, GapReport
from resume_tailorer.diff_generator import BulletChange, DiffGenerator
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.artifacts.freeform_sections import (
    comparable_content, find_sections, missing_section_anchor, profile_section,
)

from .models import ChangeCategory, ChangeDisposition, ResumeChange, ValidationStatus


AMBIGUOUS_PAIRING_THRESHOLD = 0.45
_TOKENS = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKENS.findall(text.lower()) if len(token) > 2}


def _related_gap(change: BulletChange, gap_report: GapReport) -> GapItem | None:
    change_tokens = _tokens(f"{change.original} {change.tailored}")
    ranked: list[tuple[int, int, GapItem]] = []
    for index, item in enumerate(gap_report.items):
        evidence_tokens = _tokens(f"{item.requirement} {item.candidate_evidence}")
        ranked.append((len(change_tokens & evidence_tokens), -index, item))
    if not ranked:
        return None
    overlap, _position, item = max(ranked, key=lambda value: (value[0], value[1]))
    return item if overlap else None


def _category(change: BulletChange) -> ChangeCategory:
    if change.change_type == "reordered":
        return ChangeCategory.REORDERED
    if change.change_type == "rephrased":
        return ChangeCategory.REPHRASED
    if change.change_type == "removed":
        return ChangeCategory.CONDENSED
    if change.change_type in {"modified", "added"}:
        return ChangeCategory.COMPETENCY_CHANGED
    return ChangeCategory.UNCHANGED


def revert_grammar_only_rewrites(profile: CareerTruthProfile, tailored_text: str) -> str:
    """`tailored_text` with each bullet the model reworded only in grammar or punctuation ("to
    explain" -> ", explaining") put back as it was. Such a change says nothing new for the job and
    costs the person a review (dogfood, 2026-10-13); the Word path drops them the same way."""
    diff_generator = DiffGenerator()
    text = tailored_text
    for change in diff_generator.generate_diff(profile, tailored_text).changes:
        if (change.original and change.tailored and change.original != change.tailored
                and diff_generator.same_wording(change.original, change.tailored)):
            text = text.replace(change.tailored, change.original, 1)
    return text


def build_freeform_changes(
    profile: CareerTruthProfile,
    tailored_text: str,
    gap_report: GapReport,
    review=None,
    skill_additions=(),
) -> list[ResumeChange]:
    """Build deterministic, reviewable changes for the freeform/PDF path. `skill_additions`: the
    skills with_skill_additions added by code (spec 022); the skills change carries them, and only
    the model's own wording is checked, as on the Word path."""
    from resume_tailorer.analyzers.requirement_review import introduced_unsupported, requirement_wording
    from resume_tailorer.analyzers.claim_scope import introduced_unscoped_tools

    diff_generator = DiffGenerator()
    sections = find_sections(tailored_text)
    bullet_text = tailored_text
    for span in sorted(sections.values(), key=lambda item: item.start, reverse=True):
        bullet_text = bullet_text[:span.start] + bullet_text[span.end:]
    # Keep the decision-018 global matcher intact, but don't feed section list items
    # into the work-bullet queue. The full profile is still used in truth checks below.
    bullet_profile = replace(profile, summary="", skills=[], tools=[]) if sections else profile
    diff = diff_generator.generate_diff(bullet_profile, bullet_text)
    changes: list[ResumeChange] = []
    for index, change in enumerate(diff.changes):
        similarity = change.similarity
        ambiguous = (
            bool(change.original and change.tailored)
            and similarity is not None
            and similarity < AMBIGUOUS_PAIRING_THRESHOLD
        )
        related = _related_gap(change, gap_report)
        reason = change.reasoning
        category = _category(change)
        status = ValidationStatus.PASS
        disposition = ChangeDisposition.PENDING
        unverified = (
            diff_generator.check_bullet_pair_fabrication_risk(
                change.original, change.tailored, profile,
                grounded=requirement_wording(change.original or "", review))
            if change.tailored
            else []
        )
        # Spec 010: a term the requirement review doesn't support blocks the change too.
        scope_issues = introduced_unscoped_tools(change.original or "", change.tailored or "", profile, review=review)
        unverified = [*unverified, *introduced_unsupported(change.original or "", change.tailored or "", review),
                      *scope_issues]
        if unverified:
            # Left PENDING so the user decides; the content gate blocks the
            # artifact while this text is still in it.
            status = ValidationStatus.FAIL
            reason = " ".join(unverified)
        if ambiguous:
            category = ChangeCategory.REJECTED
            status = ValidationStatus.FAIL
            disposition = ChangeDisposition.REJECTED
            reason = (
                f"Ambiguous bullet pairing ({similarity:.0%} similarity); "
                "review the source and proposed text before accepting this change."
            )

        changes.append(
            ResumeChange(
                change_id=f"freeform:{index}",
                section="work_experience",
                source_index=index,
                original_text=change.original,
                proposed_text=change.tailored,
                category=category,
                reason=reason,
                job_requirement=related.requirement if related else "",
                evidence_source=(
                    f"gap_category_{related.category.name}" if related else "career_profile"
                ),
                # A rewrite rests on its own original bullet; another bullet only for added text.
                evidence_text=change.original or (related.candidate_evidence if related else ""),
                validation_status=status,
                disposition=disposition,
                scope_issues=tuple(scope_issues),
            )
        )
    for name in ("summary", "skills"):
        if not sections:
            # An unsectioned text resume has no safe anchor for a section-level decision;
            # preserve the pre-existing bullet review behavior for that format.
            continue
        original = profile_section(profile, name)
        span = sections.get(name)
        if span is None:
            if not original:
                continue
            position = missing_section_anchor(tailored_text, name)
            proposed = ""
            baseline_span = (position, position)
        else:
            proposed = span.text
            baseline_span = (span.start, span.end)
        if comparable_content(original, name) == comparable_content(proposed, name):
            continue
        old_body = "\n".join(original.splitlines()[1:])
        new_body = "\n".join(proposed.splitlines()[1:])
        added = list(skill_additions) if name == "skills" else []
        # Only the model's wording is checked: the computed additions meet their own rules (spec 022).
        model_body = _without_terms(new_body, [a.term for a in added])
        issues = []
        scope_issues = introduced_unscoped_tools(old_body, model_body, profile, section=name, review=review)
        if model_body:
            if old_body:
                issues.extend(diff_generator.check_semantic_drift(old_body, model_body))
            issues.extend(diff_generator.check_bullet_pair_fabrication_risk(old_body, model_body, profile))
            issues.extend(introduced_unsupported(old_body, model_body, review))
            issues.extend(scope_issues)
        category = (ChangeCategory.REPHRASED if name == "summary"
                    else ChangeCategory.SKILLS_ADDED if added else ChangeCategory.COMPETENCY_CHANGED)
        changes.append(ResumeChange(
            change_id=f"freeform:{name}:0", section=name, source_index=None,
            original_text=original, proposed_text=proposed,
            category=category,
            reason=(" ".join(issues) if issues else " ".join(a.reason for a in added) if added
                    else f"{name.title()} wording changed"),
            job_requirement=", ".join(a.term for a in added), evidence_source="career_profile",
            evidence_text=old_body,
            validation_status=ValidationStatus.FAIL if issues else ValidationStatus.PASS,
            baseline_span=baseline_span,
            scope_issues=tuple(scope_issues),
            added_skills=tuple((a.term, a.level, a.reason) for a in added),
        ))
    return changes


def _without_terms(body: str, terms: list[str]) -> str:
    """A skills body without the given list items ("SQL, Excel, Tableau" without Tableau)."""
    if not terms:
        return body
    drop = {term.casefold() for term in terms}
    return "\n".join(", ".join(item for item in (part.strip() for part in line.split(","))
                               if item and item.casefold() not in drop)
                     for line in body.splitlines())
