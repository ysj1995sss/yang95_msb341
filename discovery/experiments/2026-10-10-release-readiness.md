# Release-readiness evidence — 2026-10-10

Plan: `docs/superpowers/plans/2026-10-10-release-readiness.md`.
Spec: `specs/015-streamlit-real-model-batch-verification.md`.
Start: main at `73c22fc`, six commits ahead of the local origin/main reference. Existing untracked `.claude/settings.local.json` is outside this work.

## Scope and rulings

- The builder authorized completion of steps 1–13, routine decisions and proceeding without intermediate review questions. This supersedes the earlier request to stop after each new spec.
- Test data is synthetic. Independent human participation, account consent and paid enrollment cannot be manufactured by an agent.
- The existing checkout is used as requested. Any unrelated changes will be preserved.
- Node was found at `D:/Yang/Software/cursor/NodeJs/node.exe`; the handoff's `_bak/NodeJs` location no longer exists.
- The product venv lacks FastAPI; API tests use the API venv with the product venv's site-packages appended. No dependency was installed.

## Progress

| Step | Status | Evidence |
|---|---|---|
| 1 Baseline | Passed | Product 1240 passed, 1 skipped (47.33s); API 134 passed, 276 existing warnings (30.85s); web ESLint and TypeScript exited 0; Playwright 22 passed (1.3m), clean exit 0. |
| 2 Verification spec | Written | Spec 015 and execution plan created before live tests. |
| 3 Streamlit live batch | Passed | Three real `codex-cli` Word runs; navigation during work and saved progress verified in the browser. |
| 4 Recovery/freshness | Passed | Stop/Continue, actual test-server interruption/restart, blocked stale Prepare/Apply, and single-job redo preserving the other two jobs. |
| 5 Summary review | Passed, qualified | Real PDF run plus a deterministic two-section fixture: reject Summary, accept then manually edit Skills, reload/rebuild, inspect final PDF. The fixture is not a model response. |
| 6 Web journey | Passed locally | Shared profile, live search/custom board, save, real review, PDF download, Apply tracking, Tracker. No employer submission. |
| 7 Journey fixes | Implemented | Cancellation/recovery ownership, Streamlit progress visibility/refresh, stale and older PDF handoffs, Windows profile-save retry, manual section newline. Final evidence below. |
| 8 Frontend decision | Recorded | Decision 037: Next.js primary; retain maintained Streamlit fallback. |
| 9 Model evaluation | Limited evidence recorded | Existing local model retained for supervised testing; no paid provider selected/purchased, no claim that validation establishes every fact relationship. |
| 10 Deployment preparation | Prepared | `docs/release-readiness-checklist.md`: hosting, secrets, durable data, backup/restore, two-account isolation and rollback. |
| 11 Push/CI/deployment | Release pending; deployment blocked | GitHub access verified; remote has no divergent commits. No Vercel/Render deployment connector or linked local Vercel project, no public OAuth/remote-model configuration established. |
| 12 Accessibility/integrations | Partly passed | 22 browser cases, keyboard/phone/light-dark accessibility checks; helper package built. Real Google/Gmail, Chrome extension runtime/store and human screen reader remain untested. |
| 13 Usability simulations/human protocol | Prepared/completed as agent work | Three labeled walkthroughs in `2026-10-11-agent-usability-walkthroughs.md`; P01–P03 protocol in checklist. Human participants: 0. |

## Human research

Independent participants: **0**. Agent simulations will be reported separately. No participant quotes, completion times or satisfaction ratings have been invented.

## Runtime evidence

- Initial baseline attempts had missing/permission-blocked scratch parents: product 1069 passed, 1 skipped, 171 setup errors; API 74 passed, 60 setup errors. After explicitly creating the parents, both suites passed. These setup errors are not product regressions.
- Existing Codex CLI and GitHub CLI logins are usable when read through the normal elevated approval path. Sandboxed login-status checks falsely appeared signed out; no credential was copied or printed.
- The first Next.js launch was blocked by automatic approval review running out of credits. After the builder resumed on 2026-10-11, the normal approval path started Next.js on 3300, API on 8300 and Streamlit on 8502.
- All live test servers explicitly use `product/.venv/tmp-codex/finish-20261010/live`; the real data folders were not used.
- The synthetic Word fixture imports with an education parsing warning (`BS Economics, State University, 2019`) and duplicate Tableau skill/tool warning. Education was corrected from the fixture and remaining synthetic facts confirmed in the browser. This is a usability finding, not invented participant feedback.

## Browser evidence (2026-10-11)

- Streamlit searched 75 curated boards for Data Analyst and returned 69 roles. Web read the same confirmed profile and added Watershed's public Ashby board; verification reported 35 open postings. A subsequent search used 76 boards and returned 69 matching roles.
- Batch `24816653`: Cursor User Operations, Lyft People Analytics, Lyft Go-To-Market Sales Insights. Stop while the second job ran left two completed and the third skipped. Continue started only the third. The experiment's Streamlit process was deliberately stopped mid-job; restart showed the interrupted batch with the first two reviews retained. Continue finished the remaining job. Completed review timestamps were not rewritten during continuation.
- Cursor's initial real-model review had zero meaningful changes. Lyft People proposed adding Tableau to the SQL-dashboard project. The source listed Tableau as a skill but did not explicitly link it to that project, so the agent chose **Keep original** and rebuilt. This is a quality warning about relational evidence, not an independent participant's opinion.
- Web downloaded a real synthetic PDF and tracked Cursor as ready to apply. Tracker showed one ready application, Applied: Not yet. No employer page submission or Mark as applied was performed in the live run. Automated journey tests mark only synthetic local records.
- Removing duplicate Tableau from **Tools** while retaining it in **Skills** marked all three reviews stale. Apply disabled tracking, withheld the resume/attachment and explained the profile change. Batch Prepare returned Tailor again first for all three. Retailoring Cursor made that one current while preserving both Lyft items.
- Restarted Streamlit Jobs showed the saved batch before another search. The cancelled-but-draining refresh transition is additionally covered by a real Streamlit AppTest refresh-message regression.

## PDF section exercise and live-discovered fix

- Generated and visually inspected a one-page synthetic PDF with SUMMARY, EXPERIENCE, EDUCATION and SKILLS. Uploaded it through the web's one-off control and ran the existing real model for a separate Wise role.
- **Important qualification:** the existing `session_profile.set_career_profile` gives confirmed Career Profile facts precedence over a one-off file. The run therefore used the confirmed profile (whose summary was empty), not the uploaded fixture's summary. It produced a skills reorder; this is not evidence of a model-generated summary edit. The earlier commentary describing a preserved summary was corrected by inspecting the saved run.
- Preserved the real run separately, then seeded an explicitly deterministic review with a synthetic summary rewrite and the skills reorder. No real data or live batch review was overwritten. The synthetic summary rewrite was flagged as unverified; the browser withheld downloads until it was rejected and the resume rebuilt.
- Browser actions: Keep original for Summary; Accept Skills; Edit manually using existing skills only; Save; reload; rebuild. Both decisions persisted independently.
- The first rebuilt PDF merged the next heading into `TableauEDUCATION`: the service trims manual text, but span replacement had discarded the final newline. Three failing regressions reproduced summary/skills and zero-length insertion boundaries. The fix preserves the line boundary without touching the decision-018 global matcher.
- Browser retest rebuilt version 4: original summary, manually ordered skills, separate EDUCATION, one-page PDF; the missing-Education warning disappeared. Text assertions and a rendered page inspection passed. Remaining warning: no original PDF available for render comparison. Screenshot saved outside git in the Codex visualization output folder.
- Summary/skills review was already implemented in spec 012/decision 034; the earlier decision-033 limitation is historical. Unsectioned or ambiguous headings remain a limitation, not a reason to undo the safe matcher.

## Regression and review evidence

- Batch RED: seven runner failures, two Jobs visibility failures, one cross-process recovery-lock failure, one cancelled-drain refresh failure. Final focused runner/Jobs GREEN: 38 passed. Execution IDs fence obsolete state updates; recovery rechecks under the cross-process lock; no new batch can begin while Stop drains the current hook.
- Apply RED: stale-profile routes, old in-memory/persisted handoffs after a newer batch review, and explicitly missing current PDFs. Independent public-route reproduction originally returned the old PDF with 200; after the fix, download/Track returned 409 and created no application. Opening the latest batch review restored the exact current PDF. Legacy reviews with an absent PDF key remain compatible; explicit missing PDFs fail closed.
- The first Apply full product run exposed one session-initialization failure (1248 passed, 1 failed, 1 skipped); corrected the artifact-folder fallback and reran green.
- Independent review observed a transient Windows `ProfileStore.save` replacement denial while polling. Two failing regressions reproduced it; bounded retries plus temporary-file cleanup passed all 13 profile-store tests. A first GREEN attempt had an over-strict test assertion comparing a partial record with merged defaults; corrected the synthetic fixture, then reran all 13 successfully.
- Section boundary RED: 3 failed; adjacent regeneration/truth/section GREEN: 32 passed. Independent review found two additional missing-Skills-at-EOF cases without a terminal newline; both failed before the leading-boundary fix. Final adjacent GREEN: 34 passed. No decision-018 matching change.
- Cross-frontend section retest: Streamlit loaded version 4, original Summary kept and both meaningful decisions reviewed; it displayed Ready for Apply and only the no-original-PDF render-comparison warning.

## Residual limits and access blockers

- PID reuse still falls back to the three-minute heartbeat. An obsolete worker after a false heartbeat recovery cannot alter the resumed batch state, but its already-running model hook can still write a review; execution tokens do not fence those artifact writes.
- Any profile edit invalidates every profile-derived review, including unrelated edits. One-off uploads do not supersede confirmed facts; that behavior needs clearer copy or a separately scoped product decision.
- Requirement evidence can be too generic (for example a survey-platform requirement was labeled direct against general analytical/tool facts). Project-specific tool attribution also needs scrutiny. Manual review remains required; no paid-model superiority or comprehensive quality score is established by this small sample.
- There is no connected Vercel/Render deployment capability or linked `.vercel` project in this checkout. No public Google OAuth/Gmail credentials or usable production remote-model configuration were established. No account was created, paid resource enrolled, mailbox accessed or new legal agreement accepted.
- The helper ZIP was built: `dist/job-copilot-helper-0.2.0.zip`, 9 entries, SHA256 `FB59E0211D46F5F3635FF6E957FDD05E89C685D2755BCE2B4C39EB2AAE7D3060`. Packaging and script tests do not prove Chrome extension runtime or Store publication.
- Human research and a manual NVDA/VoiceOver pass are still needed. Three agent walkthroughs are not three people, and agent approval cannot establish their feedback/consent.

## Final verification and release

Final local verification after every code fix (2026-10-11), all process exits **0**:

- Product: **1264 passed, 1 skipped**, 62.41s. `product/.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider --basetemp=.venv/tmp-codex/finish-20261010/product-final-complete-2`, with `PYTHONPATH` pointing to product. Log: `product/.venv/tmp-codex/finish-20261010/product-final-complete-2.log`.
- API: **139 passed, 276 existing warnings**, 42.87s. API venv Python, product site-packages appended with `site.addsitedir`, `pytest.main(['tests', '-q', '-m', 'not live', '-p', 'no:cacheprovider', '--basetemp=.venv/tmp-codex/finish-20261010/api-final-complete-2'])`. Log: `apps/api/.venv/tmp-codex/finish-20261010/api-final-complete-2.log`.
- Web: existing Node ran `node_modules/eslint/bin/eslint.js src e2e` and `node_modules/typescript/bin/tsc --noEmit`: no errors, exit 0.
- Browser suite: **22 passed**, 1.3m, exit 0. Existing Node ran `node_modules/@playwright/test/cli.js test`, with API venv Python and synthetic `E2E_DATA_DIR=product/.venv/tmp-codex/finish-20261010/web-final-complete-2`. Log: `product/.venv/tmp-codex/finish-20261010/e2e-release-final-2.log`.

Verified release commits:

- `1241761`: spec 015 and execution plan before implementation.
- `326a8d7`: batch ownership/recovery/progress; focused runner/Jobs check 38 passed (18.54s), exit 0.
- `20fde58`: Apply freshness; committed product checks 14 passed (5.69s), exit 0, with API covered by the final full suite.
- `75c5302`: Windows profile replacement; committed focused check 13 passed (0.25s), exit 0.
- `ee7f7e3`: reviewed section boundaries; committed adjacent check 34 passed (3.88s), exit 0.

Authorized push and remote CI are the remaining release checks. No public
deployment or account-dependent integration is claimed by these local results.
