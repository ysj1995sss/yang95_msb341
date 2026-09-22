def dedupe_key(job: dict) -> str:
    url = (job.get("original_url") or "").split("?")[0].rstrip("/").lower()
    if url:
        return f"url:{url}"
    company = (job.get("company") or "").strip().lower()
    title = (job.get("title") or "").strip().lower()
    return f"ct:{company}|{title}"
