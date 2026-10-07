"""Recognize a pasted company career-board link and verify the board is real (spec 013).

Only the link's host and path are read: nothing a person types is ever fetched. Verification
calls the platform's own fixed public API with a checked identifier, so this can't be used to
reach other sites from the server. A board is saved only when its platform confirms it exists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

PLATFORM_LABELS = {
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "ashby": "Ashby",
    "smartrecruiters": "SmartRecruiters",
}

PASTE_HINT = "Found this role somewhere else? Paste its description in Tailor."
SUPPORTED_HOSTS = "boards.greenhouse.io, jobs.lever.co, jobs.ashbyhq.com or jobs.smartrecruiters.com"

_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")

_HOSTS = {
    "boards.greenhouse.io": "greenhouse",
    "job-boards.greenhouse.io": "greenhouse",
    "boards-api.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "jobs.ashbyhq.com": "ashby",
    "jobs.smartrecruiters.com": "smartrecruiters",
    "careers.smartrecruiters.com": "smartrecruiters",
}
_EU_HOSTS = {"job-boards.eu.greenhouse.io", "boards.eu.greenhouse.io", "jobs.eu.lever.co"}
_UNSUPPORTED = {
    "myworkdayjobs.com": "Workday", "workday.com": "Workday", "icims.com": "iCIMS",
    "taleo.net": "Taleo", "linkedin.com": "LinkedIn", "indeed.com": "Indeed",
    "joinhandshake.com": "Handshake",
}
# First path words that are pages, not boards.
_NOT_TOKENS = {"embed", "v1", "jobs", "job", "search", "api", "login", "careers"}


@dataclass(frozen=True)
class BoardRef:
    platform: str
    token: str
    source_url: str

    @property
    def id(self) -> str:
        return f"{self.platform}:{self.token.lower()}"

    @property
    def platform_label(self) -> str:
        return PLATFORM_LABELS[self.platform]


@dataclass(frozen=True)
class LinkProblem:
    message: str


def parse_board_link(text: str) -> BoardRef | LinkProblem:
    raw = (text or "").strip()
    if not raw:
        return LinkProblem("Paste a link to the company's career board.")
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = "https://" + raw
    try:
        parts = urlsplit(raw)
    except ValueError:
        return LinkProblem("That doesn't look like a link. Paste the full web address.")
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return LinkProblem("That doesn't look like a link. Paste the full web address.")
    host = parts.hostname.lower().removeprefix("www.")
    if host in _EU_HOSTS:
        return LinkProblem(
            "This is a board on the platform's European site, which Job Copilot can't search yet. "
            + PASTE_HINT)
    for domain, name in _UNSUPPORTED.items():
        if host == domain or host.endswith("." + domain):
            return LinkProblem(f"{name} boards aren't supported. {PASTE_HINT}")
    platform = _HOSTS.get(host)
    if platform is None:
        return LinkProblem(
            "This page is on the company's own site. Open a job there and look for a link on "
            f"{SUPPORTED_HOSTS}, then paste that. {PASTE_HINT}")

    segments = [s for s in parts.path.split("/") if s]
    token = ""
    if platform == "greenhouse":
        query = parse_qs(parts.query)
        if segments[:1] == ["embed"]:
            token = (query.get("for") or [""])[0]
        elif host == "boards-api.greenhouse.io":
            token = segments[2] if segments[:2] == ["v1", "boards"] and len(segments) > 2 else ""
        elif segments:
            token = segments[0]
    elif segments:
        token = segments[0]
    if not token or token.lower() in _NOT_TOKENS or not _TOKEN.match(token):
        return LinkProblem(
            f"This {PLATFORM_LABELS[platform]} link doesn't name a company board. "
            "Paste the company's board page, or one of its job links.")
    return BoardRef(platform, token, f"{parts.scheme}://{host}{parts.path}")


# --- verification -------------------------------------------------------------------------

VERIFIED = "verified"
VERIFIED_EMPTY = "verified_empty"
NOT_FOUND = "not_found"
UNCONFIRMED = "unconfirmed"
UNREACHABLE = "unreachable"
SAVABLE = {VERIFIED, VERIFIED_EMPTY}


@dataclass(frozen=True)
class Verification:
    outcome: str
    name: str = ""
    postings: int = 0
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome in SAVABLE


# fetch(url) -> (HTTP status or None when unreachable, parsed JSON or None)
Fetch = Callable[[str], Tuple[Optional[int], object]]


def http_fetch(url: str, timeout: int = 15) -> Tuple[Optional[int], object]:
    import requests

    try:
        response = requests.get(url, timeout=timeout)
    except Exception:
        return None, None
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, None


def _title_name(token: str) -> str:
    return re.sub(r"[-_.]+", " ", token).strip().title() or token


def verify_board(ref: BoardRef, fetch: Fetch = http_fetch) -> Verification:
    label = ref.platform_label
    try:
        found = _check(ref, fetch)
    except Exception:
        found = (UNREACHABLE, "", 0)
    outcome, name, postings = found
    name = name or _title_name(ref.token)
    messages = {
        VERIFIED: f"Added {name} ({label}): {postings} open posting{'s' if postings != 1 else ''} right now.",
        VERIFIED_EMPTY: f"Added {name} ({label}). It has no open postings right now; future searches will check it.",
        NOT_FOUND: f"{label} has no public board called '{ref.token}'. Check the link.",
        UNCONFIRMED: ("SmartRecruiters gives the same answer for a company with no openings and one that "
                      "doesn't exist, so this board can't be confirmed. Try again when it has an opening."),
        UNREACHABLE: f"{label} didn't answer. Nothing was saved; try again.",
    }
    return Verification(outcome, name if outcome in SAVABLE else "", postings, messages[outcome])


def _check(ref: BoardRef, fetch: Fetch) -> Tuple[str, str, int]:
    t = ref.token
    if ref.platform == "greenhouse":
        status, board = fetch(f"https://boards-api.greenhouse.io/v1/boards/{t}")
        if status == 404:
            return NOT_FOUND, "", 0
        if status != 200 or not isinstance(board, dict):
            return UNREACHABLE, "", 0
        status, data = fetch(f"https://boards-api.greenhouse.io/v1/boards/{t}/jobs")
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if status != 200 or not isinstance(jobs, list):
            return UNREACHABLE, "", 0
        return (VERIFIED if jobs else VERIFIED_EMPTY), str(board.get("name") or "").strip(), len(jobs)
    if ref.platform == "lever":
        status, data = fetch(f"https://api.lever.co/v0/postings/{t}?mode=json")
        if status == 404:
            return NOT_FOUND, "", 0
        if status != 200 or not isinstance(data, list):
            return UNREACHABLE, "", 0
        return (VERIFIED if data else VERIFIED_EMPTY), "", len(data)
    if ref.platform == "ashby":
        status, data = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{t}")
        if status == 404:
            return NOT_FOUND, "", 0
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if status != 200 or not isinstance(jobs, list):
            return UNREACHABLE, "", 0
        listed = [j for j in jobs if not (isinstance(j, dict) and j.get("isListed") is False)]
        return (VERIFIED if listed else VERIFIED_EMPTY), "", len(listed)
    # SmartRecruiters answers 200 with nothing found for unknown companies, so only a board with
    # at least one posting can be confirmed.
    status, data = fetch(f"https://api.smartrecruiters.com/v1/companies/{t}/postings?limit=1")
    if status == 404:
        return NOT_FOUND, "", 0
    if status != 200 or not isinstance(data, dict) or not isinstance(data.get("content"), list):
        return UNREACHABLE, "", 0
    total = int(data.get("totalFound") or 0)
    if total < 1 or not data["content"]:
        return UNCONFIRMED, "", 0
    first = data["content"][0] if isinstance(data["content"][0], dict) else {}
    return VERIFIED, str((first.get("company") or {}).get("name") or "").strip(), total
