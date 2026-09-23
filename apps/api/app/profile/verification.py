"""
Tracks which Career Truth Profile facts were explicitly added/edited by the
user via PUT /profile, as distinct from facts the parser extracted
verbatim from the uploaded resume. Everything the parser produces is
literal resume text (no LLM inference happens at parse time -- that only
happens later, during tailoring, and is already handled by the separate
fabrication-risk/unsupported-claims machinery in diff_generator.py and
gap_analyzer.py), so a fact absent from the verification map is
"resume_verified" by construction; this module only needs to detect and
tag the fields a user's edit actually touched.

Deliberately field-diffing, not a full structural diff library: the
profile shape is small and well-known (contact_info, education[],
work_experience[] with two bullet lists each, and four flat string lists),
so a purpose-built comparison is simpler and more auditable than a generic
deep-diff dependency.
"""

RESUME_VERIFIED = "resume_verified"
USER_VERIFIED = "user_verified"

_FLAT_LIST_FIELDS = ("skills", "tools", "certifications", "accomplishments")


def _canonical(item: dict) -> str:
    return str(sorted(item.items()))


def diff_user_edits(old: dict, new: dict) -> dict[str, str]:
    """Return {field_path: USER_VERIFIED} for every fact present in `new`
    that wasn't present (verbatim) in `old` -- i.e. every genuinely
    new-or-edited fact from this specific PUT. Does not report on facts
    that are unchanged (those keep whatever verification state they
    already had, tracked by the caller merging this into the existing map)
    or facts that were removed (there's nothing to tag on a deletion)."""
    tags: dict[str, str] = {}

    old_contact = old.get("contact_info") or {}
    new_contact = new.get("contact_info") or {}
    for key, value in new_contact.items():
        if value and old_contact.get(key) != value:
            tags[f"contact_info.{key}"] = USER_VERIFIED

    if new.get("summary") and new.get("summary") != old.get("summary"):
        tags["summary"] = USER_VERIFIED

    for field in _FLAT_LIST_FIELDS:
        old_items = set(old.get(field) or [])
        for i, item in enumerate(new.get(field) or []):
            if item not in old_items:
                tags[f"{field}[{i}]"] = USER_VERIFIED

    old_education = {_canonical(e) for e in (old.get("education") or [])}
    for i, entry in enumerate(new.get("education") or []):
        if _canonical(entry) not in old_education:
            tags[f"education[{i}]"] = USER_VERIFIED

    old_jobs_by_identity = {
        (job.get("employer"), job.get("title"), job.get("dates")): job
        for job in (old.get("work_experience") or [])
    }
    for i, job in enumerate(new.get("work_experience") or []):
        identity = (job.get("employer"), job.get("title"), job.get("dates"))
        old_job = old_jobs_by_identity.get(identity)
        if old_job is None:
            tags[f"work_experience[{i}]"] = USER_VERIFIED
            continue
        for bucket in ("responsibilities", "accomplishments"):
            old_bullets = set(old_job.get(bucket) or [])
            for j, bullet in enumerate(job.get(bucket) or []):
                if bullet not in old_bullets:
                    tags[f"work_experience[{i}].{bucket}[{j}]"] = USER_VERIFIED

    return tags
