# Supervised synthetic runs: spec 012 (2026-10-06)

**Scope:** One real-model Word run and PDF/free-form runs, all from invented ATS fixtures.
No real user data, job-board visit or application submission. The configured OpenRouter free
provider returned busy on Word, so completed runs used the existing `codex-cli` integration
at medium reasoning effort; no key or account setting was changed.

## Word copy and final PDF

The synthetic Word file had an old title, date, email, summary, skills line and education year.
The Career Profile supplied corrected facts. The result was **PASS**, with no validation
findings and an 84,952-byte PDF. The report said it updated `work.dates`, `work.title`,
`contact.email`, `summary`, `skills` and `education`. Inspection of the resulting Word paragraphs
found “Senior Marketing Analyst”, “BS Economics, State University, 2020” and the updated
skills list including Tableau. One model-proposed work-bullet rephrase passed review checks.
The original Word file was held only in the local synthetic run; no master was overwritten.

## PDF/free-form review and rebuild

The first real-model PDF run failed because its summary claimed “4+ years of experience”
without confirmed evidence. The independent `freeform:summary:0` row was marked FAIL, and the
artifact was not eligible for handoff. That run also revealed a false Skills diff: the parser
had included the following `TOOLS & PLATFORMS` section in the Skills span. A focused failing
test reproduced it; the section boundary and Skills source comparison were corrected.

The subsequent real-model run produced a supported summary rewrite but two unsupported
work-bullet proposals. Initial status was **FAIL** with `UNSUPPORTED_CLAIM_PRESENT` findings.
Rejecting the failing rows and rebuilding without another model call produced **WARNING**:
the only finding was `VISUAL_CHECK_SKIPPED`, expected because the generated original PDF had
no render reference. The PDF was 2,631 bytes before rebuild; the rebuilt PDF passed content
and readability checks. The model did not change skills in this run, so live independent Skills
decisions remain unobserved; a format-2 save/reload/rebuild test covers them deterministically.

## Suite verification

- Product: 1,154 passed, 1 skipped after the final combined-contact and competencies assertions.
- API: 118 passed (275 deprecation warnings), including a blocking Word-sync `/v2` journey.
- Web lint and TypeScript: passed.
- Browser: all 20 cases reported `ok` with a fresh E2E data directory. The Windows runner did
  not exit after its final test and was stopped; this is not recorded as a clean process exit.

**Follow-up:** test one additional anonymized real template with an unusual contact or
education layout before broadening placement rules; investigate the Playwright shutdown hang
separately from product behavior.
