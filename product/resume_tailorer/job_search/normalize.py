"""Shared field normalization for job discovery (product + API)."""

from __future__ import annotations

import re
from typing import Any

YES = "YES"
NO = "NO"
POSSIBLE = "POSSIBLE"
NOT_STATED = "NOT_STATED"
UNKNOWN = "UNKNOWN"

_SPONSORSHIP_STATES = frozenset({YES, NO, POSSIBLE, NOT_STATED, UNKNOWN})


def _collapse(text: str | None) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text).strip())


def normalize_company(value: str | None) -> str:
    return _collapse(value).casefold()


def normalize_title(value: str | None) -> str:
    return _collapse(value).casefold()


def normalize_location(value: str | None) -> str:
    return _collapse(value).casefold()


def normalize_sponsorship(value: Any) -> str:
    """Map bools, enums, and free text to canonical sponsorship states.

    Silence / empty → NOT_STATED (never infer NO from missing data).
    Unrecognized non-empty text that isn't a clear yes/no/possible → UNKNOWN.
    """
    if value is None:
        return NOT_STATED
    if isinstance(value, bool):
        return YES if value else NO
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return NOT_STATED
        upper = stripped.upper().replace(" ", "_")
        aliases = {
            "YES": YES,
            "NO": NO,
            "TRUE": YES,
            "FALSE": NO,
            "POSSIBLE": POSSIBLE,
            "MAYBE": POSSIBLE,
            "NOT_STATED": NOT_STATED,
            "NOT-STATED": NOT_STATED,
            "UNKNOWN": UNKNOWN,
        }
        if upper in aliases:
            return aliases[upper]
        t = stripped.lower()
        if re.search(
            r"may be (able to )?sponsor|sponsorship may be|possible sponsorship|"
            r"sponsorship (is )?possible|case[- ]by[- ]case",
            t,
        ):
            return POSSIBLE
        if re.search(
            r"no sponsorship|not sponsor|cannot sponsor|will not sponsor|"
            r"does not sponsor|won't sponsor",
            t,
        ):
            return NO
        if re.search(
            r"sponsorship available|offers? sponsorship|h-?1b sponsorship|"
            r"will sponsor|provides sponsorship",
            t,
        ):
            return YES
        if upper in _SPONSORSHIP_STATES:
            return upper
        return UNKNOWN
    return UNKNOWN


def sponsorship_to_api(value: str) -> str:
    """Map canonical states to the API's yes/no/unknown storage literals."""
    state = normalize_sponsorship(value)
    if state == YES:
        return "yes"
    if state == NO:
        return "no"
    return "unknown"
