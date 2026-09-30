# 022: Length correction, and approved-only application answers

**Date:** 2026-09-29
**Status:** Accepted

## Length correction (audit task 6: correction loop, freeform length gate)

**Decision:** when the *only* blocking findings are length problems, run exactly one correction
pass. The DOCX length problem is `PAGE_COUNT_CHANGED`; the freeform one is the new
`PAGE_LIMIT_EXCEEDED`.

- **What gets shortened:** only bullets whose tailored text grew longer than the original. Each
  is shortened to at most its original length.
- **How:**
  - The configured model is asked to shorten the bullet without changing any fact. Its output
    is accepted only if it fits and passes the same fabrication check as any other rewrite.
  - Otherwise the bullet reverts to its original wording, which is verified and known to fit.
- **Freeform length limit:** the freeform path now enforces the length the user asked for:
  1 page, 2 pages, or the original's detected page count. Before, "preserve" allowed up to 10
  pages.
- **Where it runs:** after the first generation, in both Streamlit and the API
  (`artifacts/length_control.py`).
- **After review:** regenerating reviewed text reports an overflow but never edits that text
  automatically. The user decides.

**Rejected:**

- **Shrinking fonts or margins.** Forbidden by spec 002.
- **More than one pass.** Spec 002 bounds correction to one.
- **Letting the model shorten without checking.** A "shortened" bullet is exactly where a new
  claim could slip in.

## Custom application answers (audit task 6)

**Decision:** custom questions are answered only from an **answer bank**: answers the user typed
and approved, stored once per question and reused.

- **Nothing is drafted by a model or inferred from the resume.** Many custom questions are
  legal statements: work authorization, sponsorship, criminal history, EEO.
- **Parsers capture the visible question text** (`<label>`, `aria-label` or placeholder), and
  answers are matched on that text.
- **Previews list unanswered questions.** Launchpad lets the user answer and approve them.
- **Answers are part of the preview approval.** A changed answer requires a new preview.
- **Real submits are protected.** A real submit is still refused while any required question is
  unanswered. Answers actually used are recorded in `custom_answers`, with an `answers_version`
  hash on the application record.

**Rejected:** model-drafted answers reviewed by the user. They are tempting for "Why do you want
to work here?", but the review-fatigue risk is high, and an unreviewed legal answer is a real
harm. This can be revisited for clearly optional essay questions only, with the draft visibly
marked as a draft.

## Deferred as specs

- Status sync: `specs/005-application-status-sync.md`. The Gmail restricted-scope review makes
  it a multi-week dependency; an email-paste first slice is proposed.
- Browser Assist mode: `specs/006-browser-assist-mode.md`, a separate project. Local-only, it
  stops before Submit, and it never runs on a shared server.

## Also found

CI's first run showed that `product/requirements.txt` pinned older versions than the tests
actually pass with (pypdf 4.0.0 vs 6.19.0, reportlab 4.0.8 vs 5.0.1). Under the old pins,
original-font detection returned nothing, which likely affected the live app. The pins now
match the tested versions, and CI runs Python 3.14 like Streamlit Cloud.
