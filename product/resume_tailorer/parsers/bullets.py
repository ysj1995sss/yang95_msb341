"""Typed bullet markers ("• ", "▪ ", "- ") shared by the PDF-text and DOCX paths.

Real Word lists draw the glyph from numbering and never store it in the text
(see docx_structure.is_bullet_paragraph). Many resumes instead type the glyph
into the paragraph itself; those used to be invisible to tailoring (decision 027).
"""

from __future__ import annotations

import re

# A glyph, or a dash/asterisk/"o" that is followed by whitespace (so "-5%" or "office" never count).
# U+F0A7/U+F0B7/U+F0D8/U+F0FC/U+F076: Symbol/Wingdings bullets as Word's "Save as PDF" writes them;
# U+007F: what the PDF reader returns for the bullet in PDFs Job Copilot generates (bug hunt 2026-10-12).
_TYPED_BULLET = re.compile(r"^\s*(?:[•●▪■◦‣∙·○➢►▶✓✔➤\uf0a7\uf0b7\uf0d8\uf0fc\uf076\x7f]|[-–—*](?=\s)|o(?=\t))[\s ]*")


def typed_bullet_prefix(text: str) -> str:
    """The typed marker plus its spacing at the start of `text`, or "" if there is none."""
    match = _TYPED_BULLET.match(text or "")
    if not match or match.end() >= len((text or "").rstrip()):
        return ""  # a lone glyph with no text after it is not a bullet
    return match.group(0)


def strip_typed_bullet(text: str) -> str:
    prefix = typed_bullet_prefix(text)
    return text[len(prefix):] if prefix else text
