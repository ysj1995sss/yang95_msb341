"""Local readability check (spec 010): does the finished PDF read back, as text, with the content
it is supposed to have, in order? This runs on this computer with the same kind of text
extraction many document parsers start from. It is not a certification by any employer's ATS:
employers' systems differ, and Job Copilot can't see them.

Severity follows the builder's decision (spec 010):
- FAIL (blocks the download): the name or email is missing, or a whole bullet is missing;
- WARNING: a bullet reads back broken up or out of order (often a sign of columns), the
  replacement character � appears, or no standard Experience/Education heading is found.

The existing TEXT_NOT_EXTRACTABLE failure (no text at all) is separate and unchanged.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional

from resume_tailorer.artifacts.models import FindingCategory, FindingSeverity, ValidationFinding

NOTE = ("Readability check done on this computer. It shows whether your resume reads back as "
        "text in order; it is not a check by any employer's ATS.")

_LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "­": ""}
_STANDARD_EXPERIENCE = re.compile(
    r"^\s*(?:professional\s+|work\s+|relevant\s+)?(?:experience|employment(?:\s+history)?|work\s+history|career\s+history)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_STANDARD_EDUCATION = re.compile(r"^\s*education(?:\s+and\s+training)?\s*:?\s*$", re.IGNORECASE | re.MULTILINE)

MISSING_BELOW = 0.5  # under half of a bullet's words found anywhere: the bullet is missing
INTACT_AT = 0.85  # this share of its 4-word runs found in sequence: the bullet reads back whole


@dataclass(frozen=True)
class ExpectedContent:
    name: str = ""
    email: str = ""
    bullets: tuple[str, ...] = ()
    employers: tuple[str, ...] = ()  # in document order
    check_contact: bool = True


def normalize(text: str) -> str:
    """Text as a parser would compare it: ligatures undone, hyphenated line breaks joined,
    punctuation and spacing ignored."""
    out = text or ""
    for src, dst in _LIGATURES.items():
        out = out.replace(src, dst)
    out = unicodedata.normalize("NFKC", out)
    out = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", out)  # "manag-\nement" -> "management"
    out = re.sub(r"[^a-z0-9%$+#@.]+", " ", out.lower())
    out = re.sub(r"\.(?![a-z0-9])|(?<![a-z0-9])\.", " ", out)  # keep dots only inside emails/numbers
    return " " + re.sub(r"\s+", " ", out).strip() + " "


def _words(text: str) -> list[str]:
    return [w for w in normalize(text).split() if len(w) >= 2]


def bullet_presence(bullet: str, flat: str) -> tuple[float, float, int]:
    """(share of the bullet's words present, share of its 4-word runs present in order,
    position of the first run found or -1)."""
    words = _words(bullet)
    if not words:
        return 1.0, 1.0, -1
    present = sum(1 for w in words if f" {w} " in flat) / len(words)
    tokens = normalize(bullet).split()  # every word, so runs line up with the page text
    runs = [" ".join(tokens[i:i + 4]) for i in range(0, max(1, len(tokens) - 3))]
    found = [flat.find(f" {r} ") for r in runs]
    in_order = sum(1 for f in found if f >= 0) / len(runs)
    first = next((f for f in found if f >= 0), -1)
    return present, in_order, first


def check_readability(extracted_text: str, expected: ExpectedContent) -> list[ValidationFinding]:
    """Findings for the content the PDF should contain. Empty text is left to the existing
    TEXT_NOT_EXTRACTABLE check."""
    if not (extracted_text or "").strip():
        return []
    flat = normalize(extracted_text)
    findings: list[ValidationFinding] = []

    if expected.check_contact:
        missing = [label for label, value in (("name", expected.name), ("email", expected.email))
                   if value and normalize(value).strip() not in flat]
        if missing:
            findings.append(ValidationFinding(
                "READABILITY_CONTACT_MISSING", FindingSeverity.FAIL, FindingCategory.ATS,
                f"Your {' and '.join(missing)} didn't read back from the PDF, so a system reading it may not "
                "know whose resume it is.", {"missing": missing}))

    missing_bullets, broken, positions = [], [], []
    for bullet in expected.bullets:
        present, in_order, first = bullet_presence(bullet, flat)
        if present < MISSING_BELOW:
            missing_bullets.append(bullet)
        elif in_order < INTACT_AT:
            broken.append(bullet)
        if first >= 0:
            positions.append(first)
    if missing_bullets:
        findings.append(ValidationFinding(
            "READABILITY_BULLET_MISSING", FindingSeverity.FAIL, FindingCategory.ATS,
            f"{len(missing_bullets)} bullet(s) didn't read back from the PDF at all (for example text drawn as "
            f"an image): “{_short(missing_bullets[0])}”.", {"bullets": missing_bullets}))
    out_of_order = sum(1 for a, b in zip(positions, positions[1:]) if b < a)
    if broken or out_of_order:
        findings.append(ValidationFinding(
            "READABILITY_ORDER", FindingSeverity.WARNING, FindingCategory.ATS,
            "Some text reads back broken up or out of order, which often happens with columns or text boxes"
            + (f": “{_short(broken[0])}”." if broken else "."),
            {"broken": broken, "out_of_order": out_of_order}))

    employer_positions = [flat.find(normalize(e).rstrip()) for e in expected.employers if e]
    found_employers = [p for p in employer_positions if p >= 0]
    if any(b < a for a, b in zip(found_employers, found_employers[1:])):
        findings.append(ValidationFinding(
            "READABILITY_ROLE_ORDER", FindingSeverity.WARNING, FindingCategory.ATS,
            "Your roles read back in a different order than they appear on the page.", {}))

    if "�" in extracted_text or re.search(r"[-]", extracted_text):
        findings.append(ValidationFinding(
            "READABILITY_UNMAPPED_SYMBOLS", FindingSeverity.WARNING, FindingCategory.ATS,
            "Some symbols read back as unknown characters (�), often from icon fonts or unusual bullet "
            "symbols. Plain text symbols read back more reliably.", {}))

    if not _STANDARD_EXPERIENCE.search(extracted_text):
        findings.append(ValidationFinding(
            "READABILITY_HEADING_UNUSUAL", FindingSeverity.WARNING, FindingCategory.ATS,
            "No standard work-history heading (such as “Experience”) was found. A plain heading helps "
            "document parsers find your work history.", {"section": "experience"}))
    if not _STANDARD_EDUCATION.search(extracted_text) and _mentions_education(extracted_text):
        findings.append(ValidationFinding(
            "READABILITY_HEADING_UNUSUAL", FindingSeverity.WARNING, FindingCategory.ATS,
            "No standard “Education” heading was found.", {"section": "education"}))
    return findings


def _mentions_education(text: str) -> bool:
    return bool(re.search(r"\b(university|college|bachelor|master|mba|b\.?s\.?|b\.?a\.?)\b", text, re.IGNORECASE))


def _short(text: str, n: int = 70) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def expected_for_docx(profile, final_bullets: Iterable[str]) -> ExpectedContent:
    contact = getattr(profile, "contact_info", {}) or {}
    return ExpectedContent(
        name=str(contact.get("name") or ""), email=str(contact.get("email") or ""),
        bullets=tuple(b for b in final_bullets if b and len(_words(b)) >= 4),
        employers=tuple(j.employer for j in getattr(profile, "work_experience", []) if j.employer),
    )


def expected_for_freeform(profile) -> ExpectedContent:
    """The free-form path rewrites bullets and already checks contact details and changed text
    (content_validator), so only order, symbols and headings are checked here."""
    return ExpectedContent(employers=tuple(j.employer for j in getattr(profile, "work_experience", []) if j.employer),
                           check_contact=False)
