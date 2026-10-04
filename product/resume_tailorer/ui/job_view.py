"""Jobs master-detail view models: compact result rows and the evidence-backed
detail for one selected job. Pure; unknowns are named, never shown as zero.

Hard gates are a presentation of facts the fit scorer already produced (years
of experience, a degree requirement) plus one the posting states directly:
no visa sponsorship when the user said they need it. No second scorer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

from resume_tailorer.job_search.job_attributes import employment_type_for, experience_level_for, industry_for
from resume_tailorer.job_search.job_quality import evaluate_job_quality, quality_label
from resume_tailorer.job_search.models import FitResult, JobPosting, JobQualityStatus, TriageAction, canonicalize_triage_action

LIVE_SOURCE_LABELS = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby"}
DEMO_SOURCES = {"linkedin", "indeed", "handshake"}

ACTION_LABELS = {
    TriageAction.SAVE: "Saved",
    TriageAction.APPLY: "Preparing application",
    TriageAction.PASS: "Passed",
    TriageAction.UNREVIEWED: "New",
}


@dataclass(frozen=True)
class JobRow:
    job_id: str
    title: str
    company: str
    location: str
    work_mode: str
    salary: str
    source: str
    is_demo: bool
    freshness: str
    quality: str
    quality_tone: str
    fit: str
    fit_tone: str
    status: str


@dataclass(frozen=True)
class EvidenceLine:
    requirement: str
    evidence: str


@dataclass(frozen=True)
class JobDetail:
    row: JobRow
    url: str
    facts: tuple[tuple[str, str], ...]
    strong: tuple[EvidenceLine, ...]
    partial: tuple[EvidenceLine, ...]
    gaps: tuple[str, ...]
    hard_gates: tuple[str, ...]
    unknowns: tuple[str, ...]
    fit_parts: tuple[tuple[str, str], ...]
    summary: str


def job_id_for(job: JobPosting) -> str:
    return f"{job.source.value}_{job.source_id}"


def salary_text(job: JobPosting) -> str:
    def k(v: int) -> str:
        return f"${v // 1000}k" if v >= 1000 else f"${v}"

    if job.salary_min is None and job.salary_max is None:
        return "No salary stated"
    if job.salary_min is not None and job.salary_max is not None:
        return f"{k(job.salary_min)}–{k(job.salary_max)}"
    return f"From {k(job.salary_min)}" if job.salary_min is not None else f"Up to {k(job.salary_max)}"


def freshness_text(posted: Optional[datetime], now: Optional[datetime] = None) -> str:
    if posted is None:
        return "Post date not stated"
    now = now or datetime.now(posted.tzinfo)
    days = max((now - posted).days, 0)
    if days == 0:
        return "Posted today"
    if days == 1:
        return "Posted yesterday"
    if days < 30:
        return f"Posted {days} days ago"
    return f"Posted {posted:%b %d, %Y}"


def fit_text(fit: Optional[FitResult]) -> tuple[str, str]:
    if fit is None or fit.overall_fit is None:
        return "Fit not assessed", "neutral"
    value = round(fit.overall_fit)
    tone = "verified" if value >= 70 else "review" if value >= 40 else "blocked"
    return f"Fit {value}%", tone


def source_text(job: JobPosting) -> tuple[str, bool]:
    key = job.source.value
    if key in DEMO_SOURCES:
        return f"{key.title()} demo listing, not a real job", True
    return LIVE_SOURCE_LABELS.get(key, key.title()), False


_QUALITY_TONES = {
    JobQualityStatus.ACTIVE: "verified",
    JobQualityStatus.STALE: "review",
    JobQualityStatus.EXPIRED: "blocked",
    JobQualityStatus.BROKEN: "blocked",
}


def _work_mode_text(value: Optional[str]) -> str:
    value = (value or "").strip().lower()
    if not value or value in ("unknown", "not specified", "not stated"):
        return "Work mode not stated"
    return {"onsite": "On-site", "on-site": "On-site"}.get(value, value.capitalize())


def build_row(job: JobPosting, fit: Optional[FitResult], action: Optional[str],
              quality: Optional[JobQualityStatus] = None, now: Optional[datetime] = None) -> JobRow:
    quality = quality or evaluate_job_quality(job)
    fit_label, tone = fit_text(fit)
    source, is_demo = source_text(job)
    return JobRow(
        job_id=job_id_for(job),
        title=(job.title or "Untitled role").strip(),
        company=job.company or "Company not stated",
        location=job.location or "Location not stated",
        work_mode=_work_mode_text(job.work_mode),
        salary=salary_text(job),
        source=source,
        is_demo=is_demo,
        freshness=freshness_text(job.posted_date, now),
        quality=quality_label(quality),
        quality_tone=_QUALITY_TONES.get(quality, ""),
        fit=fit_label,
        fit_tone=tone,
        status=ACTION_LABELS.get(canonicalize_triage_action(action), "New"),
    )


def _sponsorship_text(value: Optional[bool]) -> str:
    return {True: "Sponsorship offered", False: "No sponsorship"}.get(value, "Sponsorship not stated")


def _is_hard_gate(gap: str, job: JobPosting) -> bool:
    lowered = gap.lower()
    return lowered.startswith("experience:") or bool(job.education_required and gap == job.education_required)


def _readable_gap(gap: str) -> str:
    if gap.lower().startswith("experience:"):
        return f"Asks for {gap.split(':', 1)[1].strip()} of experience; your profile shows less"
    return gap


def build_detail(job: JobPosting, fit: Optional[FitResult], action: Optional[str],
                 authorization: Optional[Mapping[str, Any]] = None,
                 quality: Optional[JobQualityStatus] = None, now: Optional[datetime] = None) -> JobDetail:
    row = build_row(job, fit, action, quality, now)
    authorization = authorization or {}
    facts = (
        ("Salary", row.salary),
        ("Work mode", row.work_mode),
        ("Sponsorship", _sponsorship_text(job.sponsorship_available)),
        ("Level", experience_level_for(job)),
        ("Job type", employment_type_for(job)),
        ("Industry", industry_for(job)),
        ("Source", row.source),
        ("Posting", f"{row.quality} · {row.freshness}"),
    )
    hard: list[str] = []
    if job.sponsorship_available is False and authorization.get("sponsorship_required") is True:
        hard.append("This employer says it doesn't sponsor visas, and you said you'll need sponsorship")
    strong: tuple[EvidenceLine, ...] = ()
    partial: tuple[EvidenceLine, ...] = ()
    gaps: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    parts: tuple[tuple[str, str], ...] = ()
    if fit is not None:
        quotes = {e.requirement: e.profile_evidence for e in fit.evidence}
        strong = tuple(EvidenceLine(r, quotes.get(r, "") or "Matched in your profile") for r in fit.strong_matches)
        partial = tuple(EvidenceLine(r, quotes.get(r, "") or "Related experience in your profile") for r in fit.partial_matches)
        hard += [_readable_gap(g) for g in fit.true_gaps if _is_hard_gate(g, job)]
        gaps = tuple(g for g in fit.true_gaps if not _is_hard_gate(g, job))
        unknowns = tuple(u.replace("preferred unmet: ", "Preferred, not in your profile: ") for u in fit.unknown)

        def pct(v: Optional[float]) -> str:
            return "Not assessed" if v is None else f"{round(v)}%"

        parts = (
            ("Eligibility", pct(fit.eligibility)),
            ("Core skills", pct(fit.core_capabilities)),
            ("Preferred skills", pct(fit.preferred_qualifications)),
            ("Evidence found", pct(fit.evidence_confidence)),
        )
    if fit is None or fit.overall_fit is None:
        summary = "Fit not assessed. Import and confirm your resume in Career Profile to see how you match."
    elif hard:
        summary = f"{len(hard)} hard {'requirement' if len(hard) == 1 else 'requirements'} may rule this out. Check before preparing an application."
    elif gaps:
        summary = f"Strong on {len(strong)}, partial on {len(partial)}, missing {len(gaps)}. Missing items will not be added to your resume."
    else:
        summary = "No gaps found against the stated requirements."
    return JobDetail(
        row=row, url=job.url or "", facts=facts, strong=strong, partial=partial, gaps=gaps,
        hard_gates=tuple(hard), unknowns=unknowns, fit_parts=parts, summary=summary,
    )
