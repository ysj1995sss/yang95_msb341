"""
Format-agnostic port of the anchor-by-year-pattern algorithm originally
written for `ResumeParser._extract_work_experience` (PDF-flattened text
only). Extracted so the exact same job-block-detection logic can also run
directly over `doc.paragraphs` for a DOCX original -- without two
implementations of the same heuristic silently drifting apart over time
the way this codebase's own history shows happens (see
resume_parser.py's "found live" comments on this exact algorithm).

Anchor = a line/paragraph containing a 4-digit year that is NOT a bullet
(e.g. "CVS Health | Woonsocket, RI    May 2026-Aug 2026"). For each anchor:
title = the nearest preceding non-blank, non-bullet line (or None if that
walk-back hits a bullet first, meaning it wandered into the previous job's
content with no title in between -- the caller decides what to do with a
missing title). body_indices = every line between this anchor and the next
(or end of input), with a trailing non-bullet line (the next job's title)
trimmed off the end -- deliberately UNFILTERED (includes non-bullet
continuation lines), since only the PDF-text caller needs to merge wrapped
continuation lines into the previous bullet (a DOCX paragraph is always one
complete logical bullet, never wrapped across paragraphs) -- that
classification is caller-specific, not part of this shared algorithm.
"""

from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

import re

YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")

T = TypeVar("T")


@dataclass
class AnchorBlock(Generic[T]):
    anchor_index: int
    title_index: int | None
    body_indices: list[int] = field(default_factory=list)


def find_anchor_blocks(
    lines: list[T],
    get_text: Callable[[T], str],
    is_bullet: Callable[[T], bool],
) -> list[AnchorBlock[T]]:
    anchor_idxs = [
        i
        for i, line in enumerate(lines)
        if YEAR_PATTERN.search(get_text(line)) and not is_bullet(line)
    ]

    blocks: list[AnchorBlock[T]] = []
    for a, idx in enumerate(anchor_idxs):
        title_index: int | None = None
        for j in range(idx - 1, -1, -1):
            candidate = get_text(lines[j]).strip()
            if not candidate:
                continue
            if not is_bullet(lines[j]):
                title_index = j
            break

        end_idx = anchor_idxs[a + 1] if a + 1 < len(anchor_idxs) else len(lines)
        bullet_range = list(range(idx + 1, end_idx))
        if a + 1 < len(anchor_idxs):
            for k in range(len(bullet_range) - 1, -1, -1):
                candidate = get_text(lines[bullet_range[k]]).strip()
                if not candidate:
                    continue
                if not is_bullet(lines[bullet_range[k]]):
                    bullet_range = bullet_range[:k]
                break

        blocks.append(
            AnchorBlock(anchor_index=idx, title_index=title_index, body_indices=bullet_range)
        )

    return blocks
