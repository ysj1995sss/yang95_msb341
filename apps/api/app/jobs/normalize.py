import re

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
    if not text or not str(text).strip():
        return UNKNOWN
    t = str(text).lower()
    if re.search(r"no sponsorship|not sponsor|cannot sponsor|will not sponsor", t):
        return "no"
    if re.search(r"sponsorship available|offers? sponsorship|h-?1b sponsorship|will sponsor", t):
        return "yes"
    return UNKNOWN


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
    elif job["sponsorship"] not in ("yes", "no", UNKNOWN):
        job["sponsorship"] = normalize_sponsorship(str(job["sponsorship"]))

    return job
