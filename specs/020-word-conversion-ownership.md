# Spec 020: Word conversion owns its own Word instance

**Status:** Approved and implemented (2026-10-12, commit c243839). Live: two-process reproduction 12/12 passed, no Word left running. Not yet checked with the builder's own Word open.
**Builds on:** decision 041 (open Word cleanup lock), decision 027 (converter order).

## Problem and evidence

Decision 041 recorded two live failures. Leaving `finalize_docx_edits`' temporary folder
raised WinError 32, because `tailored.docx` was still open in Word. Retries succeeded, so
the lock itself was never fixed.

**Reproduction (2026-10-12):**
- **Setup:** synthetic `apps/web/e2e/fixtures/resume.docx`, no Word open beforehand, the
  production `convert_docx_to_pdf`.
- **Sequential, one background thread:** 16 of 16 original+tailored pairs passed. No lock.
- **Two processes at once** (the API and Streamlit sharing one machine, as in the live run):
  - 2 of 12 pairs failed: `Word.Application.Documents`, and
    `-2147417848 The object invoked has disconnected from its clients`;
  - one pair took 83 s;
  - a hidden WINWORD process was still running after both scripts ended (0 before). It
    later exited on its own.

**Cause:** `docx2pdf.convert` calls `Dispatch("Word.Application")`, which attaches to any
running Word: another conversion's, or the person's own. It then calls `Quit()` on that
shared Word.
- One conversion can therefore shut down Word under another, leaving a document that is
  never closed, which locks it.
- The same path can also attach to, and quit, the person's own Word.

This matches the live symptoms. The exact lock holder in the 2026-10-11 run can't be
re-observed, so the claim is "same mechanism, reproduced," not "proven identical".

## Change

On Windows only, `_convert_with_word` stops using `docx2pdf` and drives Word through pywin32.
pywin32 is already installed as a `docx2pdf` dependency, so nothing new is installed.
1. **A private instance:** `DispatchEx("Word.Application")` starts a new Word process owned by
   this conversion. It never attaches to the person's Word or to another conversion's.
   Set `Visible=False` and `DisplayAlerts=0`.
2. **Open read-only:** `Documents.Open(path, ReadOnly=True, AddToRecentFiles=False,
   ConfirmConversions=False)`, then `ExportAsFixedFormat(pdf_path, 17)` (PDF).
3. **Always close what it opened:** in `finally`, `doc.Close(SaveChanges=0)`, then
   `word.Quit(SaveChanges=0)` on *this* instance only. Release the COM references, then
   `CoUninitialize`. Close and quit errors are logged and kept as the reported cause; they are
   never silently ignored. No process is ever killed by name or PID.
4. **Retry kept:** keep the existing single retry after 2 s, now with a fresh private instance.
5. **macOS unchanged:** keep `docx2pdf` there. LibreOffice is unchanged.
6. **Cleanup stays visible:** temporary-folder cleanup in the pipeline isn't wrapped in
   `ignore_cleanup_errors`. A remaining lock still surfaces as a failure, and the review
   stays resumable as today.

## Rejected

- **Killing WINWORD processes:** it could kill the person's Word.
- **Ignoring cleanup errors:** it hides the defect and leaks files.
- **A process-wide conversion lock alone:** it doesn't cover a second app or the person's own
  Word, and it serializes everything.
- **Switching to LibreOffice on Windows:** it changes layout fidelity and isn't installed here.

## Tests

- **Unit tests** (a fake COM object, so CI runs without Word):
  - a private instance is requested;
  - the document is opened read-only;
  - `Close` and `Quit` run even when export raises;
  - a close failure is reported, not swallowed;
  - the person's Word is never the target, because `Dispatch` and `GetActiveObject` aren't
    called.
- **Live on this PC** (synthetic fixture only, and only when no WINWORD is running at the
  start):
  - rerun the two-process reproduction: 0 failures and no WINWORD left afterwards;
  - check with the person's Word open that it stays open and untouched; this needs the
    builder to open a blank document.
- Run the full product and API suites.

## Out of scope

Converter choice on Linux or macOS, PDF layout, and the batch runner.
