# Decision 016: ATS capability model and a hard submission safety gate

**Date:** 2026-09-27
**Status:** Active

## Context

Auditing the existing Steps 21-24 code (per spec 003) against a stricter external brief found a
live safety bug, not just a documentation gap: `SubmissionEngine._submit_to_platform()` performs
a raw `requests.post(form_url, data=form_fields)` and treats any non-error HTTP response as a
successful real submission, then records `ApplicationStatus.APPLIED`. Decision 012 already proved
live that a real Greenhouse application form is a JS-rendered SPA with ~1 named HTML field out of
15+ visible ones, and `form_url` is the job POSTING url, not a verified form-submission endpoint.
A real click of "Confirm & Submit" today risks silently recording a false "Applied" status for a
job the user never actually applied to — directly violating the product's own stated principle
that "a submission is not complete until the system has reliable confirmation."

Separately, every ATS parser declared itself via a bare `is_supported() -> bool`, which cannot
express "Manual hand-off works, but real Assist/Auto submission doesn't" — exactly the situation
decision 012 found. Greenhouse/Lever/Ashby all return `is_supported()=True`, actively contradicting
decision 012's own verified finding when read at face value.

## Decision

Replace the bare bool with `ATSCapability` (`product/resume_tailorer/applications/models.py`): a
frozen dataclass declaring `manual_supported`, `assist_supported`, `auto_supported`,
`resume_upload`, `profile_prefill`, `custom_questions`, `final_submission`, `status_fetch`, plus a
free-text `notes` field for the honest reason. Every current parser declares
`final_submission=False` — no exceptions — because none has been proven to work against a real
form. `profile_prefill=True` for Greenhouse/Lever/Ashby specifically, because that logic (in
`FormFiller`) is real and correct for whatever fields a page does expose; the gap is that pages
expose almost none, not that prefill itself is broken.

`SubmissionEngine.apply_for_job` gates the real network POST on `capability.final_submission`,
checked as the LAST validation step immediately before `_submit_to_platform` would be called —
after form parsing, filling, and the required-field check, so Assist mode's actual value (parse,
prefill, flag what's missing) still works even for a platform that can't complete a real
submission yet. Only the final POST itself is blocked, with a clear, specific error naming the
platform and the capability gap.

The Streamlit Applications page now looks up the job's platform capability BEFORE rendering the
submit button and hard-disables "Confirm & Submit" whenever the selected mode isn't Manual and the
platform lacks `final_submission` — not just a checkbox the user can tick past. A new
`product/resume_tailorer/applications/capabilities.py` module provides this lookup so the UI
doesn't need to construct a full `SubmissionEngine` just to ask "can this actually submit?".

## Consequences

- Every existing "real submit" path against Greenhouse/Lever/Ashby now fails loudly instead of
  silently. `SubmissionEngine`'s own test suite required two existing tests to be split: one
  confirming the new block, one confirming the real-submit code path still works correctly via a
  test-only stub platform that DOES declare `final_submission=True` — the underlying mechanism was
  never wrong, only never gated on proof that it's safe to use.
  Any future integration that proves a platform supports real submission (e.g. a documented
  submission API, or verified browser automation under its own decision) only needs to flip that
  platform's `final_submission` to `True` — no other code changes required.

## What would change our mind

If a platform is verified to genuinely support a real, confirmable submission (a documented API,
or a browser-automation path with its own explicit risk-acceptance decision), flip that platform's
capability flag rather than re-architecting this gate.
