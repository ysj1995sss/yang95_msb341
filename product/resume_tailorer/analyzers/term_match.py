"""Whole-term matching for skills and tools in free text (decision 027).

A plain `\\bgo\\b` regex finds "Go" in "go-to-market", "REST" in "the rest of the
team" and can never match "C++". Terms that are also ordinary English words only
count when written the way the technology is written; every other term matches
case-insensitively as a whole token.
"""

from __future__ import annotations

import re
from functools import lru_cache

# Ordinary English words that are also technologies: (case-sensitive pattern, exclusions).
_AMBIGUOUS: dict[str, tuple[str, str]] = {
    "go": (r"\b(?:Go|Golang|golang|GoLang)\b", r"\bGo(?:-to|\s+to\b|\s+above\b|\s+beyond\b|\s+live\b|-live)"),
    "rest": (r"\bREST(?:ful)?\b|\bRESTful\b", ""),
    "spring": (r"\bSpring\b", r"\bSpring\s+(?:\d|semester|term|quarter|break|intern)"),
    "express": (r"\bExpress(?:\.js)?\b|\bexpress\.js\b|\bexpressjs\b", ""),
    "lambda": (r"\bLambda\b", ""),
    "rust": (r"\bRust\b", ""),
    "windows": (r"\bWindows\b", ""),
    "apache": (r"\bApache\b", ""),
    "hive": (r"\bHive\b", ""),
    "spark": (r"\bSpark\b|\bPySpark\b", ""),
    "swift": (r"\bSwift\b", ""),
    "testing": (r"\btesting\b", r"\btesting\s+(?:the\s+)?(?:waters|limits|boundaries)"),
}


@lru_cache(maxsize=512)
def _pattern(term: str) -> re.Pattern:
    escaped = re.escape(term.strip())
    # Token edges: no letters, digits, '+' or '#' on either side, so "c++" and "c#" work
    # and "go" is not found inside "good" or "django".
    return re.compile(rf"(?<![\w+#]){escaped}(?![\w+#])", re.IGNORECASE)


def mentions(term: str, text: str) -> bool:
    """True if `text` mentions `term` as a whole term (see module docstring)."""
    if not term or not text:
        return False
    key = term.strip().lower()
    if key in _AMBIGUOUS:
        pattern, exclude = _AMBIGUOUS[key]
        for match in re.finditer(pattern, text):
            if exclude and re.match(exclude, text[match.start():]):
                continue
            return True
        return False
    return bool(_pattern(key).search(text))


_LEAD_INS = re.compile(
    r"^(?:(?:you\s+have|you\s+bring|you'?ll\s+need|we'?re\s+looking\s+for|must\s+have|"
    r"should\s+have|ideally(?:,)?|bonus(?:\s+points)?(?:\s+if)?|plus(?:\s+if)?|nice\s+to\s+have|"
    r"preferred|required|requirements?|qualifications?)\s*:?\s*)+",
    re.IGNORECASE,
)
_QUALIFIERS = re.compile(
    r"^(?:(?:a|an|the|strong|solid|deep|proven|excellent|demonstrated|good|working|hands-on|"
    r"extensive|some|basic|advanced|familiarity|experience|knowledge|understanding|proficiency|"
    r"expertise|background|track\s+record|ability|skills?|comfort)\b(?:\s+(?:with|in|of|using|to|on))?\s*)+",
    re.IGNORECASE,
)
_TAIL = re.compile(r"\s*(?:[;:(]|,\s*(?:and|or|including|such\s+as|e\.g\.|ideally|preferably)\b|\.\s|\s+-\s).*$",
                   re.IGNORECASE)


def short_requirement(text: str, max_words: int = 8) -> str:
    """The key phrase of a requirement sentence, for lists ("SQL and Tableau" rather than
    "Strong experience with SQL and Tableau, ideally in a fast-paced environment.")."""
    original = " ".join(str(text or "").split()).strip(" -•*·")
    if not original:
        return ""
    phrase = _LEAD_INS.sub("", original)
    years = re.match(r"^(\d+\+?\s*(?:-\s*\d+\s*)?years?)\b(?:\s+of)?\s*", phrase, re.IGNORECASE)
    prefix = ""
    if years:
        prefix = years.group(1) + " "
        phrase = phrase[years.end():]
    phrase = _QUALIFIERS.sub("", phrase)
    phrase = _TAIL.sub("", phrase).strip(" .,;:")
    words = phrase.split()
    if not words:
        return original if len(original.split()) <= max_words else " ".join(original.split()[:max_words]) + "…"
    clipped = " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")
    result = (prefix + clipped).strip()
    first = result.split()[0]
    if first.isalpha() and first.islower() and len(first) > 3:  # keep "dbt", "iOS" as written
        result = result[0].upper() + result[1:]
    return result
