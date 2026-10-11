# Synthetic investigation: evidence, one-off uploads and obsolete workers

Date: 2026-10-11. Baseline: main `d577aae`.
Scope: the builder's requested next tasks 1–3 and agent testing in place of unavailable people.
Product code changes: **none**. Specs 016–018 are drafts awaiting review.

## Human versus automated evidence

Independent human participants: **0**. This run does not complete the real-person study.
No participant names, opinions, quotes, task times, ratings, consent or approvals were invented.
The agent ran the existing synthetic browser journeys and targeted deterministic diagnostics.
Existing role-based agent walkthroughs remain separately labeled in
`2026-10-11-agent-usability-walkthroughs.md`; they are not newly recruited participants.

All data was synthetic, under ignored `product/.venv/tmp-codex/spec016-20261011` or the API
test directory. No personal data folder, unrelated home `.env`, paid provider/account or
employer submission was used. No new dependency was installed; local Claude settings preserved.

## Fresh existing-suite verification

| Check | Observed result | Exit |
|---|---|---|
| Product | 1264 passed, 1 skipped; 78.03s | 0 |
| API | 139 passed, 276 existing warnings; 49.54s | 0 |
| Browser | 22 passed; 1.4m | 0 |
| Web lint and TypeScript | No errors | 0 |

Product: existing product-venv Python, `PYTHONPATH=product`, `pytest tests -q -p no:cacheprovider`
with `--basetemp=.venv/tmp-codex/spec016-20261011/product-baseline`. Log remains in that
ignored directory as `product-baseline.log`.

API: existing API-venv Python with product site-packages appended using `site.addsitedir`,
`pytest tests -q -m 'not live' -p no:cacheprovider` with
`--basetemp=.venv/tmp-codex/spec016-20261011/api-baseline`. Log in the API ignored directory.

Browser: existing Node at `D:/Yang/Software/cursor/NodeJs/node.exe`, existing Playwright CLI,
API-venv Python, explicit synthetic `E2E_DATA_DIR=product/.venv/tmp-codex/spec016-20261011/web-baseline`.
Covered profile/search/review/download/Apply/Tracker, batches, custom boards, keyboard, phone
layout, dark-theme checks and helper-script behavior. Model/board/Gmail responses are stubbed
where the suite declares that; helper script tests are not a real Chrome extension runtime.
No new real-model browser session or manual screen-reader test is claimed here.
Web lint/type checks used the existing Node with `node_modules/eslint/bin/eslint.js src e2e`
and `node_modules/typescript/bin/tsc --noEmit`.

Passing these existing tests does not establish that the gaps below are fixed.

## Three agent-led synthetic diagnostic scenarios

Script: ignored `product/.venv/tmp-codex/spec016-20261011/probes.py`, executed by the product
venv with `LITELLM_MODE=PRODUCTION`. No model call; deterministic inputs and production helpers.
Final execution: exit **0**, all three scenarios completed. Its first attempt exited 1 because
the minimal saved review fixture omitted the loader's required `changes` key; adding `changes=[]`
corrected the diagnostic fixture. That failure is not a new product regression.

### S01 — Inspect a suggested claim and a named-platform requirement

- Synthetic Example A bullet: `Built SQL dashboards and analytics reports.`
- Synthetic Example B bullet: `Built Tableau dashboards for inventory planning.`
- Posting: `Experience with SQL and Tableau.`
- Adding `using Tableau` to Example A's bullet produced `introduced_unsupported=[]` and
  `manual_validation=[]`. Expected safety outcome: no proof ties Tableau to this project.
- Separate posting: `Experience with analytics platforms such as Qualtrics.`
- Actual row: terms `[Analytics]`, status `direct`, evidence the SQL analytics bullet.
  Expected outcome: generic analytics cannot establish Qualtrics experience.

Root cause: supported terms are aggregated across the review/profile; the pair fabrication
checker also permits profile-wide terms. Missing Qualtrics vocabulary lets a generic match
decide the row. Spec 016 proposes claim-local guards and explicit named-platform handling.

### S02 — Upload a different summary while a Career Profile is loaded

- Loaded fact-vault summary: `Confirmed SQL analyst`.
- Synthetic upload summary: `Distinct uploaded summary`.
- `set_career_profile(..., RESUME_UPLOAD)` returned the existing fact-vault object; effective
  summary remained `Confirmed SQL analyst`, source `fact_vault`.
- Trace: API one-off calls the service with `career_profile=None`/`provenance=None`; the service
  parses the file but uses this setter's result. Its saved `profile_version` comes from the
  parameter, not the effective object. This explains both disclosure and bookkeeping risks.

This is a setter reproduction and code-path trace, not a new model-generated PDF/Word result.
Spec 017 retains saved-profile precedence, explains file versus facts, and records effective
source/provenance/version accurately. It does not silently create an override/merge feature.

### S03 — Continue an interrupted job before the old worker returns

- Blocked a worker, injected an expired heartbeat, recovered and continued the same job.
- Current worker saved a minimal format-2 review with marker `current` and synthetic PDF bytes.
- Released the old worker; production `save_review` overwrote the review with marker `old`.
- Execution token changed on Continue and remained current afterward; batch state stayed `done`.
  Review marker nevertheless changed from `current` to `old`.

Root cause: runner tokens fence status, not side effects inside `Hooks.tailor_one`.
This probe used production storage and runner functions, with deliberately minimal hooks;
it is not a real-model or multi-process artifact test. Spec 018 requires staging plus atomic,
locked ownership-checked publication and acceptance through both actual frontend hooks.

## Proposed order and review gate

1. Review spec 016; implement truthful evidence guards with new failing pipeline regressions.
2. Review spec 017; disclose actual source behavior and correct its effective-source bookkeeping.
3. Review spec 018; implement fenced artifact publication with two-process race tests.
4. Repeat synthetic browser/model exercises after each implemented change, then obtain real
   user feedback when people are available. Do not claim human comprehension from these tests.

These specifications are separate to keep changes reviewable. No implementation plan or
product fix is approved by this investigation. No push/deployment is authorized by this turn.
