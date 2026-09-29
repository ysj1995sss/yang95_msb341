"""Pure filter + sort helpers for the Job Discovery Dashboard (Step 7).

No Streamlit / FastAPI imports — shared by the Streamlit page and API list
router so filter/sort behavior stays in parity.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from resume_tailorer.job_search.job_quality import evaluate_job_quality
from resume_tailorer.job_search.models import (
    DashboardFilters,
    JobPosting,
    JobQualityStatus,
    canonicalize_triage_action,
)
from resume_tailorer.job_search.normalize import normalize_sponsorship

SORT_OPTIONS = (
    "posted_date",
    "fit_score",
    "salary",
    "company",
    "deadline",
    "title",
)

_SALARY_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([kK])?")


def parse_salary_min(value: Any) -> Optional[int]:
    """Extract a lower-bound salary integer from int/float/str forms."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text or text.lower() in {"unknown", "not specified", "n/a"}:
        return None
    matches = _SALARY_NUM_RE.findall(text.replace(",", ""))
    if not matches:
        return None
    amounts: List[int] = []
    for num, suffix in matches:
        amount = float(num)
        if suffix.lower() == "k":
            amount *= 1000
        amounts.append(int(amount))
    return min(amounts) if amounts else None


def _job_salary_floor(job: JobPosting) -> Optional[int]:
    if job.salary_min is not None:
        return job.salary_min
    return job.salary_max


def _matches_keyword(job: JobPosting, keyword: str) -> bool:
    needle = keyword.strip().casefold()
    if not needle:
        return True
    haystacks = [
        job.company or "",
        job.title or "",
        job.location or "",
        job.description or "",
    ]
    return any(needle in (h.casefold()) for h in haystacks)


def _matches_sponsorship(job: JobPosting, wanted: str) -> bool:
    wanted_norm = wanted.strip().upper().replace(" ", "_")
    if wanted_norm in {"", "ANY", "ALL"}:
        return True
    aliases = {
        "YES": "YES",
        "NO": "NO",
        "POSSIBLE": "POSSIBLE",
        "NOT_STATED": "NOT_STATED",
        "UNKNOWN": "UNKNOWN",
        "NOT-STATED": "NOT_STATED",
    }
    target = aliases.get(wanted_norm, wanted_norm)
    return normalize_sponsorship(job.sponsorship_available) == target


def filter_and_sort_jobs(
    jobs: Sequence[JobPosting],
    filters: DashboardFilters,
    *,
    fit_scores: Optional[Dict[str, Optional[float]]] = None,
    actions: Optional[Dict[str, Optional[str]]] = None,
    quality_by_id: Optional[Dict[str, JobQualityStatus]] = None,
    now: Optional[datetime] = None,
) -> List[JobPosting]:
    """Apply dashboard filters then sort. Pure function."""
    fit_scores = fit_scores or {}
    actions = actions or {}
    quality_by_id = quality_by_id or {}
    clock = now or datetime.now()

    def _job_id(job: JobPosting) -> str:
        return f"{job.source.value}_{job.source_id}"

    filtered: List[JobPosting] = []
    for job in jobs:
        jid = _job_id(job)

        if filters.action and filters.action != "all":
            action = actions.get(jid)
            if filters.action == "unreviewed":
                if canonicalize_triage_action(action).value != "unreviewed":
                    continue
            elif canonicalize_triage_action(action) != canonicalize_triage_action(
                filters.action
            ):
                continue

        score = fit_scores.get(jid)
        if filters.min_fit is not None:
            if score is None or score < filters.min_fit:
                continue
        if filters.max_fit is not None:
            if score is None or score > filters.max_fit:
                continue

        if filters.min_salary is not None:
            floor = _job_salary_floor(job)
            if floor is None or floor < filters.min_salary:
                continue

        if filters.sponsorship and not _matches_sponsorship(job, filters.sponsorship):
            continue

        if filters.work_mode:
            mode = (job.work_mode or "").strip().casefold()
            wanted_mode = filters.work_mode.strip().casefold()
            if wanted_mode not in {"", "any", "all"} and mode != wanted_mode:
                continue

        if filters.source:
            wanted_source = filters.source.strip().casefold()
            if wanted_source not in {"", "any", "all"}:
                if job.source.value.casefold() != wanted_source:
                    continue

        if filters.quality:
            wanted_q = filters.quality.strip().casefold()
            if wanted_q not in {"", "any", "all"}:
                quality = quality_by_id.get(jid)
                if quality is None:
                    quality = evaluate_job_quality(job, now=clock)
                if quality.value != wanted_q:
                    continue

        if filters.keyword and not _matches_keyword(job, filters.keyword):
            continue

        filtered.append(job)

    return sort_jobs(
        filtered,
        sort_by=filters.sort_by,
        sort_dir=filters.sort_dir,
        fit_scores=fit_scores,
    )


def sort_jobs(
    jobs: Sequence[JobPosting],
    *,
    sort_by: str = "posted_date",
    sort_dir: str = "desc",
    fit_scores: Optional[Dict[str, Optional[float]]] = None,
) -> List[JobPosting]:
    """Sort jobs by a supported field."""
    fit_scores = fit_scores or {}
    key = (sort_by or "posted_date").strip().lower()
    reverse = (sort_dir or "desc").strip().lower() != "asc"

    def _jid(job: JobPosting) -> str:
        return f"{job.source.value}_{job.source_id}"

    def _value(job: JobPosting) -> Any:
        if key == "fit_score":
            return fit_scores.get(_jid(job))
        if key == "salary":
            return _job_salary_floor(job)
        if key == "company":
            return (job.company or "").casefold()
        if key == "title":
            return (job.title or "").casefold()
        if key == "deadline":
            return comparable_datetime(job.application_deadline)
        return comparable_datetime(job.posted_date)

    # Jobs missing the sort value always go last, whichever direction is chosen.
    known = [job for job in jobs if _value(job) is not None]
    missing = [job for job in jobs if _value(job) is None]
    return sorted(known, key=_value, reverse=reverse) + missing


def comparable_datetime(value: Optional[datetime]) -> Optional[datetime]:
    """Naive UTC, so dates from sources with and without timezones can be compared."""
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def filter_api_job_dicts(
    items: Sequence[Dict[str, Any]],
    *,
    min_fit: Optional[float] = None,
    max_fit: Optional[float] = None,
    min_salary: Optional[int] = None,
    sponsorship: Optional[str] = None,
    work_mode: Optional[str] = None,
    source: Optional[str] = None,
    quality: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "fit_score",
    sort_dir: str = "desc",
) -> List[Dict[str, Any]]:
    """Filter/sort API-shaped job dicts (JobListItem-like) for list parity."""
    filtered: List[Dict[str, Any]] = []
    for item in items:
        score = item.get("fit_score")
        if min_fit is not None and (score is None or score < min_fit):
            continue
        if max_fit is not None and (score is None or score > max_fit):
            continue

        if min_salary is not None:
            floor = parse_salary_min(item.get("salary"))
            if floor is None or floor < min_salary:
                continue

        if sponsorship:
            wanted = sponsorship.strip().lower()
            if wanted not in {"", "any", "all"}:
                actual = (item.get("sponsorship") or "unknown").strip().lower()
                # API stores yes/no/unknown; accept product YES/NO/NOT_STATED too
                aliases = {
                    "yes": "yes",
                    "no": "no",
                    "unknown": "unknown",
                    "not_stated": "unknown",
                    "not-stated": "unknown",
                    "possible": "unknown",
                }
                if aliases.get(wanted, wanted) != aliases.get(actual, actual):
                    continue

        if work_mode:
            wanted_mode = work_mode.strip().casefold()
            if wanted_mode not in {"", "any", "all"}:
                actual_mode = (item.get("work_mode") or "").strip().casefold()
                if actual_mode != wanted_mode:
                    continue

        if source:
            wanted_source = source.strip().casefold()
            if wanted_source not in {"", "any", "all"}:
                if (item.get("source") or "").strip().casefold() != wanted_source:
                    continue

        if quality:
            wanted_q = quality.strip().casefold()
            if wanted_q not in {"", "any", "all"}:
                if (item.get("quality_status") or "unknown").strip().casefold() != wanted_q:
                    continue

        if keyword:
            needle = keyword.strip().casefold()
            blob = " ".join(
                str(item.get(k) or "")
                for k in ("company", "title", "location", "description")
            ).casefold()
            if needle and needle not in blob:
                continue

        filtered.append(item)

    key = (sort_by or "fit_score").strip().lower()
    reverse = (sort_dir or "desc").strip().lower() != "asc"

    def _api_value(item: Dict[str, Any]) -> Any:
        if key == "posted_date" or key == "posted_at":
            return item.get("posted_at") or None
        if key == "salary":
            return parse_salary_min(item.get("salary"))
        if key == "company":
            return (item.get("company") or "").casefold()
        if key == "title":
            return (item.get("title") or "").casefold()
        if key == "deadline":
            val = item.get("deadline")
            return None if not val or val == "unknown" else val
        return item.get("fit_score")

    known = [item for item in filtered if _api_value(item) is not None]
    missing = [item for item in filtered if _api_value(item) is None]
    return sorted(known, key=_api_value, reverse=reverse) + missing
