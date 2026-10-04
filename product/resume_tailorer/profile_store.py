"""The Career Profile on disk: one versioned JSON file per user, plus every resume
version they uploaded (spec 007, open decision 1 = A).

Lives in the user's existing data folder next to job_search.db and
applications.db, so the same isolation rules apply (decision 023). Resume files
are written once and never overwritten; each upload is a new version.

No Streamlit import. Parsing lives in profile_import.py.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = 1

# Provenance of a fact. "missing" is derived, never stored.
FROM_RESUME = "resume"
EDITED = "edited"
CONFIRMED = "confirmed"

CONTACT_FIELDS = ("name", "email", "phone", "location")


def empty_record() -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "profile": {},
        "provenance": {},
        "resume": None,
        "resume_history": [],
        "facts_confirmed_at": None,
        "no_education": False,
        "links": {"linkedin": "", "portfolio": "", "github": ""},
        "preferences": {},
        # Legally significant answers. Only ever set from what the user chose.
        "authorization": {"authorized_to_work": None, "sponsorship_required": None},
        "updated_at": None,
    }


def fact_paths(profile: dict) -> list[str]:
    """Every provenance-tracked fact path present in a profile."""
    paths = [f"contact_info.{k}" for k in CONTACT_FIELDS if (profile.get("contact_info") or {}).get(k)]
    if (profile.get("summary") or "").strip():
        paths.append("summary")
    paths += [f"work_experience[{i}]" for i, _ in enumerate(profile.get("work_experience") or [])]
    paths += [f"education[{i}]" for i, _ in enumerate(profile.get("education") or [])]
    for key in ("skills", "tools", "certifications"):
        if profile.get(key):
            paths.append(key)
    return paths


class ProfileStore:
    """Reads and writes one user's Career Profile folder."""

    def __init__(self, folder: str | Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / "career_profile.json"

    def load(self) -> dict:
        record = empty_record()
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                stored = json.load(f)
            record.update(stored)
            for key in ("links", "authorization"):
                merged = empty_record()[key]
                merged.update(stored.get(key) or {})
                record[key] = merged
        return record

    def save(self, record: dict) -> dict:
        record = copy.deepcopy(record)
        record["schema"] = SCHEMA_VERSION
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        fd, tmp = tempfile.mkstemp(dir=self.folder, suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=1, ensure_ascii=False)
        os.replace(tmp, self.path)
        return record

    def mtime(self) -> float:
        return self.path.stat().st_mtime if self.path.exists() else 0.0

    def save_resume_file(self, record: dict, filename: str, data: bytes) -> dict:
        """Store a new immutable resume version and return its metadata."""
        version = len(record.get("resume_history") or []) + 1
        ext = os.path.splitext(filename)[1].lower() or ".bin"
        stored_name = f"resume_v{version}{ext}"
        with open(self.folder / stored_name, "xb") as f:
            f.write(data)
        meta = {
            "filename": os.path.basename(filename),
            "stored_as": stored_name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
            "version": version,
            "kind": ext.lstrip("."),
            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        }
        record.setdefault("resume_history", []).append(meta)
        record["resume"] = meta
        return meta

    def resume_bytes(self, meta: Optional[dict]) -> Optional[bytes]:
        if not meta:
            return None
        path = self.folder / meta["stored_as"]
        if not path.exists():
            return None
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != meta.get("sha256"):
            return None  # never use a file that isn't the version on record
        return data


def set_fact(record: dict, path: str, state: str = EDITED) -> None:
    record.setdefault("provenance", {})[path] = state


def confirm_remaining(record: dict) -> int:
    """Mark every fact still only 'from resume' as confirmed. Returns how many."""
    count = 0
    provenance = record.setdefault("provenance", {})
    for path in fact_paths(record.get("profile") or {}):
        if provenance.get(path, FROM_RESUME) == FROM_RESUME:
            provenance[path] = CONFIRMED
            count += 1
    record["facts_confirmed_at"] = datetime.now().isoformat(timespec="seconds")
    return count


def provenance_of(record: dict, path: str) -> str:
    profile = record.get("profile") or {}
    if path not in fact_paths(profile):
        return "missing"
    return (record.get("provenance") or {}).get(path, FROM_RESUME)


def _value_at(profile: dict, path: str) -> Any:
    if path.startswith("contact_info."):
        return (profile.get("contact_info") or {}).get(path.split(".", 1)[1], "")
    if "[" in path:
        key, index = path[:-1].split("[")
        items = profile.get(key) or []
        return items[int(index)] if int(index) < len(items) else None
    return profile.get(path)


def apply_edits(record: dict, new_profile: dict) -> list[str]:
    """Replace the profile with the user's edited version. Every fact whose
    value changed is marked as edited by the user. Returns the changed paths."""
    old = record.get("profile") or {}
    changed = []
    for path in sorted(set(fact_paths(old)) | set(fact_paths(new_profile))):
        if _value_at(old, path) != _value_at(new_profile, path):
            changed.append(path)
    record["profile"] = new_profile
    provenance = record.setdefault("provenance", {})
    present = set(fact_paths(new_profile))
    for path in list(provenance):
        if path not in present:
            provenance.pop(path)
    for path in changed:
        if path in present:
            provenance[path] = EDITED
    return changed


def combined_bullets(job: dict) -> list[str]:
    """A job's bullet points as one list, in resume order (what it did, then results)."""
    return list(job.get("responsibilities") or []) + list(job.get("accomplishments") or [])


def split_bullets(job: dict, lines: list[str]) -> tuple[list[str], list[str]]:
    """Store edited bullets back. A line that was a result stays a result, so an
    untouched job keeps its exact shape and isn't marked as edited."""
    results = set(job.get("accomplishments") or [])
    return [l for l in lines if l not in results], [l for l in lines if l in results]
