"""Stable job fingerprinting for identity, dedupe, and triage continuity."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from resume_tailorer.job_search.models import JobPosting
from resume_tailorer.job_search.normalize import (
    normalize_company,
    normalize_location,
    normalize_title,
)


_TRACKING_PARAMS = {"gclid", "fbclid", "ref", "referrer", "source", "src", "gh_src", "lever-source", "trk", "mc_cid", "mc_eid"}


def _is_tracking_param(name: str) -> bool:
    name = name.lower()
    return name.startswith("utm") or name in _TRACKING_PARAMS


def normalize_url(url: str | None) -> str:
    """Drop tracking params, fragment, and trailing slash; lowercase host+path.

    Identifying params are kept: many career sites address each job only by a
    query param (e.g. ?gh_jid=123), so stripping every param merges different jobs.
    """
    if not url or not str(url).strip():
        return ""
    parsed = urlparse(str(url).strip())
    kept = sorted(
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_param(key)
    )
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            urlencode(kept),
            "",
        )
    )


def job_fingerprint(posting: JobPosting) -> str:
    """Stable identity key for a posting.

    Preference order:
    1. Normalized canonical URL
    2. source:source_id when source_id is present
    3. ct:company|title|location (normalized)
    """
    url_key = normalize_url(getattr(posting, "url", None))
    if url_key:
        return f"url:{url_key}"

    source_id = (getattr(posting, "source_id", None) or "").strip()
    source = getattr(posting, "source", None)
    source_value = source.value if hasattr(source, "value") else str(source or "")
    if source_id and source_value:
        return f"src:{source_value}:{source_id}"

    company = normalize_company(getattr(posting, "company", None))
    title = normalize_title(getattr(posting, "title", None))
    location = normalize_location(getattr(posting, "location", None))
    return f"ct:{company}|{title}|{location}"


def job_dict_fingerprint(job: dict) -> str:
    """Fingerprint for API-shaped job dicts (original_url / external_ids)."""
    url_key = normalize_url(job.get("original_url") or job.get("url"))
    if url_key:
        return f"url:{url_key}"

    external_ids = job.get("external_ids") or {}
    source = (job.get("source") or "").strip().lower()
    source_id = ""
    if isinstance(external_ids, dict):
        source_id = (
            external_ids.get(source)
            or external_ids.get("id")
            or next(iter(external_ids.values()), "")
        )
    source_id = str(source_id or "").strip()
    if source and source_id:
        return f"src:{source}:{source_id}"

    company = normalize_company(job.get("company"))
    title = normalize_title(job.get("title"))
    location = normalize_location(job.get("location"))
    return f"ct:{company}|{title}|{location}"


def legacy_job_dict_fingerprint(job: dict) -> str | None:
    """The URL key used before query params were kept, or None if unchanged.

    Rows stored under the old key are re-keyed on their next upsert so their
    triage state carries over instead of a duplicate row being created.
    """
    new_key = job_dict_fingerprint(job)
    if not new_key.startswith("url:"):
        return None
    parsed = urlparse(new_key[len("url:"):])
    if not parsed.query:
        return None
    return "url:" + urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
