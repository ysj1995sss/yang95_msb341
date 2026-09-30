"""Split a job description into sections by its own heading lines.

Real postings name their sections in many ways ("Who You Are:", "You might
thrive in this role if you have:", "Bonus Points:", "IN THIS ROLE, YOU
WILL:"). Each heading is classified as required, preferred, responsibilities,
or other (company blurb, benefits, legal text); a section runs until the next
heading, so benefits and EEO text never leak into requirements.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

REQUIRED = "required"
PREFERRED = "preferred"
RESPONSIBILITIES = "responsibilities"
OTHER = "other"

# Checked in this order: "Preferred Qualifications" is preferred, not required.
_CLASSES = [
    (PREFERRED, r"prefer|nice[\s-]*to[\s-]*have|bonus|plus(es)?\b|extra credit|ideally|good to have|"
                r"what you'?ll bring|what you bring"),
    (REQUIRED, r"require|qualification|must|what you'?ll need|what you need|looking for|who you are|"
               r"you might thrive|you have|about you|your background|skills and experience|experience you|"
               r"what you'?ll have|basic qual|minimum|look for|^experience\b|great fit|good fit|"
               r"successful in this role"),
    (RESPONSIBILITIES, r"responsib|what you'?ll do|what you will do|in this role|you will\b|your role|"
                       r"day[\s-]to[\s-]day|you'?ll be doing|objectives|what you'?ll own|the work"),
]
# Standard legal/pay boilerplate: once it starts, the posting's requirements have ended.
_BOILERPLATE = re.compile(
    r"equal (?:employment )?opportunit|e-verify|reasonable accommodation|pay (?:range )?transparency|"
    r"privacy (?:policy|notice)|affirmative action",
    re.I,
)
_SMALL_WORDS = {"a", "an", "and", "the", "of", "for", "to", "in", "on", "with", "or", "at", "by", "you", "your", "we", "our"}
_BULLET = re.compile(r"^\s*(?:[-*•▪◦]|\d+[.)])\s+")
_INLINE_HEADING = re.compile(r"^([A-Za-z][^:]{2,70}?):\s*(\S.*)$")


def classify_heading(text: str) -> str:
    lowered = text.lower().replace("’", "'")
    for label, pattern in _CLASSES:
        if re.search(pattern, lowered):
            return label
    return OTHER


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or _BULLET.match(stripped) or len(stripped) > 80:
        return False
    if stripped.endswith(":"):
        return True
    words = stripped.split()
    letters = [ch for ch in stripped if ch.isalpha()]
    if letters and stripped.upper() == stripped and len(words) <= 10:
        return True
    # Short Title Case lines without sentence punctuation ("What You'll Do",
    # "About MongoDB") are headings; real list items are rarely Title Case.
    if len(words) > 8 or stripped[-1] in ".!?,;":
        return False
    if words[0].lower() == "about":
        return True
    content = [w for w in words if w[0].isalpha() and w.lower() not in _SMALL_WORDS]
    return bool(content) and all(w[0].isupper() for w in content)


def split_sections(text: str) -> Optional[Dict[str, List[str]]]:
    """Items per section class, or None when the text has no classified headings."""
    sections: Dict[str, List[str]] = {REQUIRED: [], PREFERRED: [], RESPONSIBILITIES: []}
    current: Optional[str] = None
    found = False
    bullets_in_section = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if _is_heading(line):
            current = classify_heading(line)
            found = found or current != OTHER
            bullets_in_section = False
            continue
        is_bullet = bool(_BULLET.match(line))
        inline = _INLINE_HEADING.match(line) if not is_bullet else None
        if inline and classify_heading(inline.group(1)) != OTHER and len(inline.group(1).split()) <= 8:
            current = classify_heading(inline.group(1))
            found = True
            bullets_in_section = False
            line = inline.group(2)
        elif _BOILERPLATE.search(line):
            current = None
        elif not is_bullet and bullets_in_section:
            # A plain paragraph after a bulleted list is the posting moving on
            # (pay notice, company blurb, legal text) without a heading.
            current = None
        bullets_in_section = bullets_in_section or is_bullet
        if current in sections:
            item = _BULLET.sub("", line).strip()
            if item:
                sections[current].append(item)
    return sections if found else None
