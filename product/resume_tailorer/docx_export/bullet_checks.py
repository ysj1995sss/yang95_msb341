"""Soft (non-blocking) per-bullet checks for the DOCX splice pipeline."""


def bullet_length_delta(original: str, new: str, warn_threshold: float = 0.35) -> list[str]:
    """
    Warn when a rewritten bullet's character count grew by more than
    `warn_threshold` (35%) relative to the original -- a cheap, render-free
    proxy for "this bullet is at real risk of wrapping onto an extra line."
    Not a hard reject: the actual page-count hard gate is the docx2pdf
    round-trip comparison in pipeline.py, which is the only way to know for
    certain whether Word's own line-wrapping pushed the document to an
    extra page.
    """
    if not original:
        return []
    delta = (len(new) - len(original)) / len(original)
    if delta > warn_threshold:
        preview = new if len(new) <= 60 else new[:60] + "..."
        return [
            f"Bullet grew {delta:.0%} longer ({len(original)} -> {len(new)} chars): "
            f"'{preview}' -- may wrap onto an extra line."
        ]
    return []
