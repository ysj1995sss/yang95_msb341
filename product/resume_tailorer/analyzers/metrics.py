"""Number-bearing tokens in resume text (a metric, a scale, a count), read the same way by the
rewrite check (diff_generator) and the finished-PDF check (pdf/content_validator)."""

from __future__ import annotations

import re

# A unit sticks to its number: "$120M", "3x", "15%". With a space allowed, "by 2027" + "Managed" read as
# "2027 M" (million), a metric no correct PDF contains (builder's resume, 2026-10-12).
METRIC_RE = re.compile(r"\$?\d[\d,.]*(?:%|[kmb](?![a-z])|x(?![a-z])|×|\+|-person|-year|s\b)?", re.I)


def metric_tokens(text: str) -> set[str]:
    """Each metric once, without the sentence punctuation after it: "in 2019," is the same 2019 as
    "in 2019 across"."""
    return {match.group().strip().rstrip(",.") for match in METRIC_RE.finditer(text)} - {""}
