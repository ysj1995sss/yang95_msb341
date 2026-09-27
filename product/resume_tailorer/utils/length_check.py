"""
Soft (non-blocking) bullet length-growth check, shared between the DOCX
splice pipeline and the freeform/PDF tailoring path.

Lives in utils/ (not docx_export/) so diff_generator.py can use it too
without a circular import: diff_generator.py is imported BY
docx_bullet_tailorer.py, which is imported by docx_export/pipeline.py,
which docx_export/__init__.py imports at package-init time -- so
diff_generator.py importing anything from the docx_export package
(even a leaf module with no imports of its own) would trigger that whole
chain and cycle back to itself.
"""


def bullet_length_delta(original: str, new: str, warn_threshold: float = 0.35) -> list[str]:
    """
    Warn when a rewritten bullet's character count grew by more than
    `warn_threshold` (35%) relative to the original -- a cheap, render-free
    proxy for "this bullet is at real risk of wrapping onto an extra line."
    Not a hard reject: the DOCX path's actual page-count hard gate is the
    docx2pdf round-trip comparison in pipeline.py, which is the only way to
    know for certain whether Word's own line-wrapping pushed the document
    to an extra page. The freeform/PDF path has no equivalent hard gate at
    all -- length there is a pure post-hoc rendering concern (font/margin
    adjustment) -- so this warning is the only length signal it gets at
    generation-adjacent time.
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
