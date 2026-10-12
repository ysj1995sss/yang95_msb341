# Spec 019: Tailor review verification — 2026-10-12

## Scope and diagnosis

The builder's Tailor screenshot showed 13 rows with repeated, clipped labels
and a failed two-page artifact. We inspected the labels and reproduced two
different source edits mapped to the same job requirement with synthetic
changes. The old queue used the requirement as its label, causing the apparent
repeat. We did **not** reproduce duplicate underlying proposals from the
builder's real resume, which was not inspected. A separate synthetic control
keeps identical wording at different source positions independently decidable;
an exact same-occurrence repeat is not automatically accepted. Decision 018's
global diff matcher was not changed.

## Build and safety checks

Commits `060a45e` through `28fe54f` add distinct titles, versioned shared
decision mutation, conservative assistance, API batch/mode support, Next.js
full-text/batch review, and Streamlit parity. A follow-up safety check caught
that a `REPHRASED` category alone could omit an original metric or detail; a
failing synthetic test preceded a stricter lexical preservation gate. Existing
safe-rewrite tests still pass. Follow-up commit `a92fe4f` contains that gate
and the synthetic end-to-end assisted-mode journey.

TDD evidence: new tests were observed red before changes for absent title and
transaction functions, mode and batch endpoints, browser review controls,
Streamlit mode/selection, stale Streamlit save, legacy origin, and omitted
substantive detail. Focused final tests: review/assistance product tests **23
passed**, exit 0; review persistence **16 passed**, exit 0. The API's focused
workspace Tailor tests passed before full suite verification.

Synthetic browser checks exercised manual mode, full original/proposed and job
requirement text, multi-selection including keyboard use, selected-only
accept/reject, conflict reload, failed-artifact download/Apply gate,
AI-assisted choice before run, visible origin, override and rebuild, and
screen accessibility. The simulated model, board, and converter in
`apps/api/tests/e2e_server.py` were used, never a personal resume or employer
submission. The full 29-case Playwright run printed `ok` for every case,
including mobile/dark-theme cases, but Windows left the runner open after the
servers closed; it was interrupted. **Do not interpret this as suite exit 0.**
The first full browser attempt exposed a test-only wrong expectation after a
human override; the second exposed an ambiguous old test selector after adding
the batch button. Both tests were corrected and the later 29 cases printed
`ok`. No real-model or independent-person usability evidence is claimed.

The final product/API suite results and lint/typecheck are recorded in the
latest handoff after their processes finish. An initial concurrent full-suite
run had one product process-race fixture miss its 15-second startup deadline;
that test passed alone, and the product suite passed when rerun without the API
suite competing for resources. The API full suite passed **154 tests**, 282
warnings, exit 0. Web lint/types passed exit 0.

## Open checks

- An independent read-only review was requested but could not start because
  the owner's review spend cap was reached. This is not an approval.
- Obtain a clean Playwright exit on this Windows runner or CI; all printed
  cases passing is narrower evidence than suite completion.
- Supervise a live-model run with synthetic data, particularly a Word resume
  with meaningful edits and the known temporary DOCX cleanup risk.
- No human participants, deployment, account integration, merge, or push were
  performed here.
