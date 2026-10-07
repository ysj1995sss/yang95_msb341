"""A person's own added company career boards (spec 013).

Stored in their profile record under `custom_boards`, so both apps share them and "Your data"
export and delete cover them. Only boards their platform verified are ever saved. Removing a
board keeps the jobs, triage and applications that came from it (decision 020's rule).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from resume_tailorer.job_search.board_links import (
    PLATFORM_LABELS,
    BoardRef,
    LinkProblem,
    Verification,
    parse_board_link,
    verify_board,
)

FIELD = "custom_boards"
MAX_CUSTOM_BOARDS = 25
NOT_SPECIFIED = "Not specified"


def curated_boards(platform: str) -> Dict[str, tuple]:
    from resume_tailorer.job_search import job_attributes as attrs

    return {
        "greenhouse": attrs.COMPANY_DIRECTORY,
        "lever": attrs.LEVER_BOARDS,
        "ashby": attrs.ASHBY_BOARDS,
        "smartrecruiters": attrs.SMARTRECRUITERS_BOARDS,
    }[platform]


def boards_in(record: Optional[dict]) -> List[dict]:
    """The saved boards; records from before spec 013 have none. Malformed entries are skipped."""
    found = []
    for entry in (record or {}).get(FIELD) or []:
        if (isinstance(entry, dict) and entry.get("platform") in PLATFORM_LABELS
                and isinstance(entry.get("token"), str) and entry.get("token")):
            found.append(entry)
    return found


def board_id(platform: str, token: str) -> str:
    return f"{platform}:{token.lower()}"


@dataclass(frozen=True)
class AddResult:
    ok: bool
    code: str  # added | link | duplicate | curated | limit | not_found | unconfirmed | unreachable
    message: str
    board: Optional[dict] = None


def precheck(record: dict, ref: BoardRef) -> Optional[AddResult]:
    """Reasons not to add, found before any network request."""
    if any(board_id(b["platform"], b["token"]) == ref.id for b in boards_in(record)):
        return AddResult(False, "duplicate", "You've already added this board.")
    curated = curated_boards(ref.platform)
    match = next((token for token in curated if token.lower() == ref.token.lower()), None)
    if match is not None:
        return AddResult(False, "curated",
                         f"{curated[match][0]} ({ref.platform_label}) is already searched by default.")
    if len(boards_in(record)) >= MAX_CUSTOM_BOARDS:
        return AddResult(False, "limit",
                         f"You can add up to {MAX_CUSTOM_BOARDS} boards. Remove one to add another.")
    return None


def add_board(record: dict, link: str, *, name: str = "", industry: str = "",
              fetch=None, now: Optional[datetime] = None) -> AddResult:
    """Parse, check, verify and (only when verified) save. Changes `record` in place on success."""
    ref = parse_board_link(link)
    if isinstance(ref, LinkProblem):
        return AddResult(False, "link", ref.message)
    refused = precheck(record, ref)
    if refused is not None:
        return refused
    from resume_tailorer.job_search import board_links

    result: Verification = verify_board(ref, fetch or board_links.http_fetch)
    if not result.ok:
        return AddResult(False, result.outcome, result.message)
    stamp = (now or datetime.now()).isoformat(timespec="seconds")
    from resume_tailorer.job_search.job_attributes import INDUSTRY_OPTIONS

    entry = {
        "id": ref.id,
        "platform": ref.platform,
        "token": ref.token,
        "name": (name or "").strip()[:80] or result.name,
        "industry": industry if industry in INDUSTRY_OPTIONS else NOT_SPECIFIED,
        "source_url": ref.source_url,
        "added_at": stamp,
        "verified_at": stamp,
        "postings_at_check": result.postings,
        "last_search": None,
    }
    record[FIELD] = [*boards_in(record), entry]
    message = result.message
    if entry["name"] != result.name:
        message = message.replace(result.name, entry["name"], 1)
    return AddResult(True, "added", message, entry)


def remove_board(record: dict, wanted_id: str) -> bool:
    boards = boards_in(record)
    kept = [b for b in boards if board_id(b["platform"], b["token"]) != wanted_id]
    record[FIELD] = kept
    return len(kept) != len(boards)


def extra_boards(boards: Iterable[dict]) -> Dict[str, Dict[str, Tuple[str, str]]]:
    """{platform: {token: (company name, industry)}} for the scrapers."""
    grouped: Dict[str, Dict[str, Tuple[str, str]]] = {}
    for b in boards:
        grouped.setdefault(b["platform"], {})[b["token"]] = (
            b.get("name") or b["token"], b.get("industry") or NOT_SPECIFIED)
    return grouped


def industry_labels(boards: Iterable[dict]) -> Dict[str, str]:
    """{company name (lowercase): industry} for boards the person labeled."""
    return {(b.get("name") or "").strip().lower(): b["industry"] for b in boards
            if b.get("industry") and b["industry"] != NOT_SPECIFIED and b.get("name")}


def record_search_results(record: dict, results: Dict[str, dict], at: str) -> None:
    """Store each added board's outcome from the last search: {"status", "matched"}."""
    boards = boards_in(record)
    for b in boards:
        outcome = results.get(board_id(b["platform"], b["token"]))
        if outcome is not None:
            b["last_search"] = {"at": at, "status": outcome.get("status", "failed"),
                                "matched": int(outcome.get("matched") or 0)}
    record[FIELD] = boards


def added_board_keys(boards: Iterable[dict]) -> set:
    """(platform, lowercase token) pairs, to label postings that came from an added board."""
    return {(b["platform"], b["token"].lower()) for b in boards}
