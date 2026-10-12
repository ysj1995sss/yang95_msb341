# Decision 042: Clear Tailor review with conservative assistance

Date: 2026-10-12. Scope: approved spec 019, implemented locally on
`codex/truthful-tailoring-sources-publication`. Evidence:
`discovery/experiments/2026-10-12-spec-019-tailor-review.md`.

## Choices

- Keep manual review as the default. Let the person choose AI-assisted review
  **before** starting a new run; never reinterpret an already saved review when
  they change that preference. Both frontends display every decision's origin
  and reason. Legacy reviews without origin say "Origin not recorded."
- Use the existing proposal and deterministic checks, not another model call.
  Assistance accepts only anchored, passing rephrases that retain every
  substantive original word and have no scope issue; it keeps the original
  for individually failed proposals; uncertainty stays undecided. This lexical
  preservation rule is deliberately strict: a good synonym may need human
  review rather than a risky silent omission. It is not a guarantee of truth.
- Show distinctive original-to-proposed queue titles and full text. Repeated
  job requirements are not proof of duplicate edits. Keep different source
  occurrences separately decidable; leave an exact same-occurrence repeat
  undecided for a person. Do not disturb decision 018's global matcher.
- Apply selected decisions in one cross-process locked, revision-checked
  transaction. Reject invalid or stale selections without partial writes.
  Streamlit's ordinary session save also checks its saved baseline under this
  lock, so it cannot replace a newer API/other-tab review.
- Reuse regeneration and final validation. Accepting a proposal, manually or
  automatically, never turns a failed PDF into a downloadable/applicable one.

## Rejected and limits

An extra LLM judge would add cost and give another fallible approval path.
Client-side loops of single-change requests could partially apply a selection.
Collapsing rows by shared requirement or similar text could delete distinct
source occurrences or their saved IDs. AI assistance does not submit employer
applications, promise an ATS result, or replace final human judgment.

No dependency, real user data, push, merge, deployment, or new account was part
of this work. The independent review could not run because the workspace owner
spend cap was reached. The Windows Playwright runner printed all 29 passing
cases but lingered after server shutdown and was interrupted, so an exit-0
browser suite is not claimed. Live-model behavior remains unverified; the
existing Word temporary-file lock, deployment/integrations, and human usability
work remain open.
