"""API job dedupe keys — delegates to the product fingerprint helper."""

from resume_tailorer.job_search.fingerprint import job_dict_fingerprint, legacy_job_dict_fingerprint


def dedupe_key(job: dict) -> str:
    return job_dict_fingerprint(job)


def legacy_dedupe_key(job: dict) -> str | None:
    return legacy_job_dict_fingerprint(job)
