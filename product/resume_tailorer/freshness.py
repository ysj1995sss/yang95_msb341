"""Is a saved tailored resume still based on the person's current Career Profile? (spec 014)

A run from the Career Profile records the profile's content hash. When the profile changes later
(any edit), the review says so, and preparing it for applying asks to tailor it again first: the
resume may contradict facts the person has since corrected. Reviews saved before spec 014, and
runs from a one-off file, have no version, and nothing is claimed about them.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

STALE_CHIP = "Profile changed"


def profile_version(profile) -> Optional[str]:
    """Content hash of a Career Profile (canonical JSON, then sha256)."""
    if profile is None:
        return None
    canonical = json.dumps(dataclasses.asdict(profile), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Freshness:
    stale: Optional[bool]  # None: not known (an older review, or a one-off file)
    message: str = ""


def _when(value: Any) -> str:
    try:
        moment = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return ""
    return f" ({moment:%b} {moment.day})"


def review_freshness(state: Optional[dict], profile) -> Freshness:
    if not state or not state.get("profile_version") or profile is None:
        return Freshness(None)
    if state["profile_version"] == profile_version(profile):
        return Freshness(False)
    return Freshness(True, f"Your Career Profile changed after this was tailored{_when(state.get('tailored_at'))}. "
                           "Tailor it again to use your current profile.")


TAILOR_AGAIN_FIRST = "Your Career Profile changed after this was tailored. Tailor it again first."
