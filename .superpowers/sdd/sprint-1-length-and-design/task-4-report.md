# Task 4 Report: Wire target_length and style_hints into the Streamlit UI

**Status:** DONE

**Commits:** 24b4a80ab577b1ad5434df46ab9e47ffe4207be8

**Test Summary:** 198 passed, 0 failed (`pytest tests/ -v` from `product/`), 79.80s. No new automated tests added (UI wiring only, as specified). Syntax validated via `python -c "import ast; ast.parse(open('resume_tailorer/app.py', encoding='utf-8').read())"` — no errors.

## What was found in app.py

Read `product/resume_tailorer/app.py` in full before editing. Key findings that differ from the brief's illustrative placeholder code:

1. **Raw resume text was NOT available anywhere in app.py or in `ResumeParser`.** `ResumeParser.parse(file_path)` (in `product/resume_tailorer/parsers/resume_parser.py`) extracts text internally via `_extract_text_from_pdf`/`_extract_text_from_docx` and immediately converts it into a `CareerTruthProfile` — it never returns or exposes the raw text. There was no public method to get raw text, and Task 3 did not add one (it only added `extract_style_hints(raw_text)`, which expects the caller to already have the text). Since modifying the parser's public `parse()` signature was out of scope for this task and risked breaking Task 1-3's tests, I had the UI call the parser's existing private extraction helpers (`parser._extract_text_from_pdf` / `parser._extract_text_from_docx`) directly, based on the uploaded file's suffix — mirroring exactly the same logic `parse()` uses internally, so there's no drift risk. This happens before the `finally` block deletes the temp file, so the file is still present.

2. **Variable names**: the parsed profile is called `profile` (a `CareerTruthProfile`), not `career_profile`. `st.session_state["career_profile"] = profile` was indeed already present from an earlier fix (line ~91), confirming this is the right place in the flow to also derive style hints. I added `parser = ResumeParser()` (previously it was `ResumeParser().parse(...)` inline with no retained instance) so the same instance could be reused for `.extract_style_hints(...)`.

3. **PDFGenerator.generate() call** used positional args `(optimization_result.tailored_resume, profile.name)` — no `job_title` kwarg was ever passed in this codebase (unlike the brief's illustrative snippet which included `job_title=job_title`). I did not invent a `job_title` variable that doesn't exist; I only added `target_length=target_length` and `style_hints=style_hints` as new keyword args, leaving the existing two positional args untouched.

4. **PDFValidator.validate() call** was `PDFValidator().validate(pdf_path)` — added `target_length=target_length` as the brief specified.

5. **New UI control**: added a third sidebar section, "3. Choose the target resume length", with the exact `st.selectbox` / `target_length_map` code the brief specified, placed after the job description text area and before the "Tailor my resume" button, so `target_length` is resolved before the button-click branch runs.

## Concerns

None. All 198 existing tests (183 prior + 15 from Tasks 1-3) still pass, syntax is valid, and the flow was traced end-to-end: selectbox -> `target_length` -> `PDFGenerator.generate(target_length=..., style_hints=...)` and `PDFValidator.validate(target_length=...)`. The one deviation from the brief's illustrative code (using the parser's private extraction methods instead of a nonexistent public "raw text" accessor) was necessary because no such public interface exists yet in this codebase; it was flagged rather than silently worked around.

## Fix Round 1

**Finding addressed:** `app.py` reached into `ResumeParser`'s private methods `_extract_text_from_pdf`/`_extract_text_from_docx` directly, duplicating `parse()`'s file-type dispatch logic (encapsulation violation + duplication/drift risk).

### What was changed

1. **`product/resume_tailorer/parsers/resume_parser.py`**
   - Added a new public method `get_raw_text(self, file_path: str) -> str` (inserted immediately after `parse()`, before `_extract_text_from_pdf`). It contains the exact dispatch logic that used to live inline in `parse()`: checks `Path(file_path).suffix.lower()`, calls `_extract_text_from_pdf` for `.pdf`, `_extract_text_from_docx` for `.docx`/`.doc`, and raises `ValueError(f"Unsupported file format: {path.suffix}")` otherwise — identical exception type and message format as the original `parse()` code, so no existing test's expected exception changes.
   - Refactored `parse()` to just call `text = self.get_raw_text(file_path)` then `return self._parse_text(text)`. Behavior is 100% identical — same exceptions, same text, same downstream call — since the dispatch logic was moved, not altered.
   - There is now exactly one place the `.pdf`/`.docx`/`.doc` dispatch branching lives: inside `get_raw_text()`.

2. **`product/resume_tailorer/app.py`**
   - Removed the duplicated inline dispatch block (previously calling `parser._extract_text_from_pdf(resume_path)` / `parser._extract_text_from_docx(resume_path)` based on a locally recomputed `suffix`, falling back to `""` for unrecognized suffixes).
   - Replaced it with:
     ```python
     try:
         raw_resume_text = parser.get_raw_text(resume_path)
     except ValueError:
         raw_resume_text = ""
     ```
   - Removed the now-unused `from pathlib import Path` import (Path was only used for the removed suffix computation; nothing else in `app.py` references `Path`).
   - `style_hints = parser.extract_style_hints(raw_resume_text)` is unchanged — it still receives an empty string in the (unreachable in practice, since `resume_path` already passed `parser.parse(...)` earlier in the same flow) unsupported-format case, preserving the original UI behavior of never crashing at this line.

3. **`product/tests/test_resume_parser.py`**
   - Added `test_get_raw_text_dispatches_pdf` — asserts `get_raw_text()` on the existing `sample_resume_path` PDF fixture returns a string containing "John Smith" (mirrors the existing PDF-extraction test's fixture and assertion style).
   - Added `test_get_raw_text_raises_on_unsupported_extension` — asserts `parser.get_raw_text("resume.txt")` raises `ValueError` matching "Unsupported" (matches the file's existing `pytest` import and flat function-style test conventions; no new imports needed).

### Test results

Command: `cd product && python -m pytest tests/ -v`

Result: **200 passed in 73.94s** (198 prior + 2 new `get_raw_text` tests). No failures, no changes to any other test's pass/fail status.

Syntax check: `python -c "import ast; ast.parse(open('resume_tailorer/app.py', encoding='utf-8').read())"` from `product/` — no errors (`OK`).

### Confirmation that `parse()`'s behavior is unchanged

- `parse()`'s dispatch logic (suffix check, private-method calls, `ValueError` message text `f"Unsupported file format: {path.suffix}"`) was moved verbatim into `get_raw_text()` — no branch conditions, exception types, or messages were altered.
- `parse()` now delegates to `get_raw_text()` and passes its return value unchanged into `self._parse_text(text)`, exactly as before.
- All pre-existing `test_resume_parser.py` tests that call `parser.parse(...)` (`test_resume_parser_extracts_text_from_pdf`, `test_resume_parser_extracts_contact_info`, `test_resume_parser_extracts_education`, `test_resume_parser_extracts_work_experience`) pass unchanged, confirming `parse()`'s external behavior is identical.
- `app.py`'s flow was re-traced end-to-end: `parser.parse(resume_path)` succeeds first (line ~105) using a format that is therefore known-supported, so the subsequent `parser.get_raw_text(resume_path)` call (for style hints) will not raise `ValueError` in practice; the `except ValueError: raw_resume_text = ""` branch is a defensive fallback matching the original code's intent, exactly as instructed.

### Concerns

None. The `_extract_text_from_pdf`/`_extract_text_from_docx` private methods are no longer referenced from outside `ResumeParser` anywhere in `product/resume_tailorer/`.
