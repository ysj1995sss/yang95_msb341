"""The skills line of a Word resume (spec 022): where change levels 2-3 may add skills.

Only an unambiguous list counts: the paragraph right under a single "Skills" heading, or one
"Skills: ..." line. Anything else (no list, or two skills sections) is left alone, so additions
are shown as unplaced rather than guessed into the wrong paragraph. A "Core Competencies:" line is
the competencies target (docx_structure), not this one.
"""

from __future__ import annotations

import re

_HEADING = re.compile(r"^\s*(?:technical\s+|key\s+|core\s+)?skills(?:\s*(?:and|&)\s*tools)?\s*:?\s*$", re.IGNORECASE)
_INLINE = re.compile(r"^\s*(?:technical\s+|key\s+)?skills(?:\s*(?:and|&)\s*tools)?\s*:\s*\S", re.IGNORECASE)
_COMPETENCIES = re.compile(r"^\s*core\s+competencies\s*:", re.IGNORECASE)
_SEPARATORS = (" | ", "; ", " • ", " · ", ", ")


def _looks_like_list(text: str) -> bool:
    body = text.split(":", 1)[1] if _INLINE.match(text) else text
    items = [item.strip() for item in re.split(r"[,|;•·]", body) if item.strip()]
    return len(items) >= 2 and all(len(item) <= 40 for item in items)


def find_skills_paragraph_index(paragraphs) -> int | None:
    """Index of the one skills-list paragraph, or None when there isn't exactly one."""
    found: list[int] = []
    for i, paragraph in enumerate(paragraphs):
        text = paragraph.text.strip()
        if not text or _COMPETENCIES.match(text):
            continue
        if _INLINE.match(text) and _looks_like_list(text):
            found.append(i)
        elif _HEADING.match(text):
            following = next((j for j in range(i + 1, len(paragraphs)) if paragraphs[j].text.strip()), None)
            if following is not None and _looks_like_list(paragraphs[following].text.strip()):
                found.append(following)
            else:
                return None  # a skills section we can't read as a list: never guess
    return found[0] if len(found) == 1 else None


def append_skills(text: str, terms: list[str]) -> str:
    """`text` with `terms` added at the end, using the line's own separator and final full stop."""
    body, trail = text.rstrip(), ""
    if body.endswith("."):
        body, trail = body[:-1], "."
    separator = next((s for s in _SEPARATORS if s in body), ", ")
    return body + "".join(separator + term for term in terms) + trail
