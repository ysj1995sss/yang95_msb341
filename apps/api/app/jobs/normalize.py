"""API job payload normalization — shared product helpers + API storage shape."""

from resume_tailorer.job_search.normalize import (
    normalize_sponsorship as product_normalize_sponsorship,
    sponsorship_to_api,
)

UNKNOWN = "unknown"

_OPTIONAL_UNKNOWN_FIELDS = (
    "work_mode",
    "salary",
    "posted_at",
    "deadline",
    "employment_type",
    "ats_platform",
)


def normalize_sponsorship(text: str | None) -> str:
    return sponsorship_to_api(product_normalize_sponsorship(text))


def _missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def normalize_job_payload(raw: dict) -> dict:
    job = dict(raw)
    if _missing(job.get("external_ids")):
        job["external_ids"] = {}

    for field in _OPTIONAL_UNKNOWN_FIELDS:
        if _missing(job.get(field)):
            job[field] = UNKNOWN

    if _missing(job.get("sponsorship")):
        job["sponsorship"] = normalize_sponsorship(job.get("description"))
    else:
        job["sponsorship"] = sponsorship_to_api(job["sponsorship"])

    return job
