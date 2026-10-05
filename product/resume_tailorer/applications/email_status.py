"""Read a pasted recruiter email: which application it is about and what status it
suggests (spec 005, first slice). Pure and deterministic: no model sets a status, and
nothing changes until the user confirms in Tracker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Iterable, Optional

from resume_tailorer.analyzers.term_match import mentions
from resume_tailorer.applications.models import ApplicationStatus

# Most decisive first: a rejection that also says "thank you for applying" is a rejection.
_RULES: tuple[tuple[ApplicationStatus, tuple[str, ...]], ...] = (
    (ApplicationStatus.OFFER, (
        r"pleased to (?:extend|offer)", r"extend (?:you )?an offer", r"offer letter", r"offer of employment",
        r"verbal offer",
    )),
    (ApplicationStatus.REJECTED, (
        r"(?:decided|chosen|chose) to (?:move forward|proceed|pursue) with other candidates",
        r"(?:will not|won't|not) (?:be )?(?:moving|move) forward", r"not to (?:move|proceed) forward",
        r"(?:position|role) has (?:already )?been filled", r"regret to inform", r"other candidates whose",
        r"unable to offer you", r"not (?:been )?selected", r"no longer (?:being )?considered",
    )),
    (ApplicationStatus.WITHDRAWN, (r"(?:you have|you've|has been) withdrawn", r"withdrawal of your application",)),
    (ApplicationStatus.FINAL_INTERVIEW, (r"final(?:-| )round", r"final interview", r"on-?site interview", r"super ?day",)),
    (ApplicationStatus.ASSESSMENT, (
        r"(?:online|technical|skills) assessment", r"coding (?:challenge|exercise|test)", r"take-?home",
        r"hackerrank", r"codesignal", r"codility", r"case study", r"complete (?:the|this|an) assessment",
    )),
    (ApplicationStatus.INTERVIEW, (
        r"(?:schedule|invite you to|set up) (?:an |a |your )?(?:\w+ )?interview", r"interview with (?:the )?(?:team|hiring)",
        r"hiring manager (?:interview|conversation|call)", r"panel interview", r"next round",
    )),
    (ApplicationStatus.RECRUITER_SCREEN, (
        r"phone screen", r"recruiter (?:call|screen|chat)", r"introductory call", r"screening call",
        r"(?:quick|brief|short) (?:call|chat)", r"(?:15|20|30)[- ]minute (?:call|chat|conversation)",
        r"learn more about your background",
    )),
    (ApplicationStatus.APPLIED, (
        r"received your application", r"thank you for (?:applying|your application)",
        r"application (?:has been|was) (?:received|submitted)",
    )),
)

# Funnel order, to warn when a suggestion would move an application backwards.
_ORDER = [ApplicationStatus.APPLIED, ApplicationStatus.ASSESSMENT, ApplicationStatus.RECRUITER_SCREEN,
          ApplicationStatus.INTERVIEW, ApplicationStatus.FINAL_INTERVIEW, ApplicationStatus.OFFER]

_STOP = {"senior", "junior", "lead", "principal", "staff", "the", "and", "for", "with", "ii", "iii", "i"}


@dataclass(frozen=True)
class Candidate:
    application_id: str
    company: str
    role: str
    status: ApplicationStatus


@dataclass(frozen=True)
class Match:
    application_id: str
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EmailReading:
    status: Optional[ApplicationStatus]
    phrase: str  # the words that suggested the status
    matches: tuple[Match, ...]  # best first
    chosen: Optional[str]  # set only when exactly one application clearly matches
    email_date: Optional[date]
    subject: str

    def moves_backwards(self, current: ApplicationStatus) -> bool:
        if self.status not in _ORDER or current not in _ORDER:
            return False
        return _ORDER.index(self.status) < _ORDER.index(current)


def suggest_status(text: str) -> tuple[Optional[ApplicationStatus], str]:
    for status, patterns in _RULES:
        for pattern in patterns:
            found = re.search(pattern, text, re.IGNORECASE)
            if found:
                return status, found.group(0)
    return None, ""


def _header(text: str, name: str) -> str:
    found = re.search(rf"^{name}:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
    return found.group(1).strip() if found else ""


def _email_date(text: str) -> Optional[date]:
    raw = _header(text, "Date") or _header(text, "Sent")
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).date()
    except (TypeError, ValueError):
        pass
    for fmt in ("%A, %B %d, %Y %I:%M %p", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.split(" at ")[0].strip(), fmt).date()
        except ValueError:
            continue
    return None


def _role_words(role: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", role.lower()) if len(w) > 2 and w not in _STOP}


def match_applications(text: str, candidates: Iterable[Candidate]) -> tuple[Match, ...]:
    sender = _header(text, "From").lower()
    words = set(re.findall(r"[a-z]+", text.lower()))
    found = []
    for c in candidates:
        score, reasons = 0, []
        company = c.company.strip()
        if company and mentions(company, text):
            score, reasons = score + 2, [*reasons, f"names {company}"]
        token = re.sub(r"[^a-z0-9]", "", company.lower())
        if token and token in re.sub(r"[^a-z0-9@.]", "", sender):
            score, reasons = score + 1, [*reasons, "sent from the company"]
        if c.role and mentions(c.role, text):
            score, reasons = score + 2, [*reasons, f"names the role {c.role}"]
        else:
            role = _role_words(c.role)
            if role and len(role & words) / len(role) >= 0.5:
                score, reasons = score + 1, [*reasons, "mentions the role"]
        if score:
            found.append(Match(c.application_id, score, tuple(reasons)))
    return tuple(sorted(found, key=lambda m: -m.score))


def read_email(text: str, candidates: Iterable[Candidate]) -> EmailReading:
    candidates = list(candidates)
    status, phrase = suggest_status(text)
    matches = match_applications(text, candidates)
    by_id = {c.application_id: c for c in candidates}
    chosen = None
    if matches:
        best = matches[0]
        tied = len(matches) > 1 and matches[1].score == best.score
        names_company = any(r.startswith("names ") and not r.startswith("names the role") for r in best.reasons)
        if not tied and best.score >= 2 and names_company and best.application_id in by_id:
            chosen = best.application_id
    subject = _header(text, "Subject")
    return EmailReading(status, phrase, matches, chosen, _email_date(text), subject)
