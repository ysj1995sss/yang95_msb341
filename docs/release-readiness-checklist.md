# Job Copilot release checklist

Prepared 2026-10-11 under spec 015. This is an execution checklist, not evidence that
hosting, Google consent, Chrome publishing or human research has passed. Record actual
results in `discovery/experiments/2026-10-10-release-readiness.md`; use passed, failed,
blocked or untested and retain the commit, runtime and date.

## 1. Hosting: API first, web second

Prerequisites: repository access in the intended Render and Vercel accounts, permission
to use an existing suitable service/disk, a Google Web application OAuth client, and a
remote model credential with a defined spending limit. The Render blueprint requests a
`starter` Docker service and a 1 GB persistent disk; check the account's current terms
before creating a paid resource. Local `codex-cli` is refused for signed-in workspace
users and cannot supply the public deployment's model.

- [ ] Record the tested commit and CI results. Keep Streamlit available; the existing
      Community Cloud single-user demo is not a multi-user fallback.
- [ ] In Render, import this repository as a Blueprint using `render.yaml`. Docker build
      context is the repository root; Dockerfile is `apps/api/Dockerfile`; health path
      is `/health`. Keep one API instance while its data and batch state use a local disk.
- [ ] Confirm disk `/data` is mounted and writable. The Docker image supplies
      `JOB_COPILOT_DATA_DIR=/data`, `APP_ENV=production` and `LEGACY_ROUTES=false`.
      Workspace routes use per-user JSON/files and SQLite databases; no separate
      Postgres service or legacy `DATABASE_URL` is required in this configuration.
- [ ] Enter secrets directly in the hosting dashboard or an approved secret manager.
      Never put their values in this file, screenshots, chat, build output or git.

| Host | Variable | Value to supply |
|---|---|---|
| API + web | `WORKSPACE_TOKEN_SECRET` | Same private random value on both, at least 32 characters; generate 64 for this deployment |
| API | `LLM_MODEL` | Supported remote model identifier, not `codex-cli` |
| API | `LLM_API_KEY` | Credential for that provider |
| API | `LLM_FALLBACK_MODELS` | Optional deliberate provider/model choices; leave empty if none |
| API | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Optional for Gmail; same OAuth client used by the web |
| API | `ERROR_WEBHOOK_URL` | Optional existing alert destination; no new destination is required |
| Web | `API_URL` | API HTTPS origin, without `/v2` or a trailing slash |
| Web | `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET` | Google Web application client's ID and secret |
| Web | `AUTH_SECRET` | Separate private random value, at least 32 characters |
| Web | `PRIVACY_CONTACT` | Monitored contact address, set privately in deployment settings |

- [ ] In Vercel, import the repository, select Next.js and root directory `apps/web`.
      Use the package scripts and lockfile; do not configure a static export. Set
      variables for the intended environment, then deploy again after changing them.
      A preview that shares production's API also shares its data; use a separate
      test API/client for experiments. See [Vercel root settings](https://vercel.com/docs/project-configuration/general-settings#root-directory)
      and [environment variables](https://vercel.com/docs/environment-variables).
- [ ] Set Google redirect URLs as in section 3. Check `/privacy` without signing in.
- [ ] Open the deployed web from another device. Sign in as test account A, import a
      synthetic resume, search, tailor, reject an unsafe change, rebuild, download,
      prepare and track. Repeat with account B: profile, jobs, artifacts, answers,
      reviews and Tracker rows must remain separate.
- [ ] Redeploy/restart the API and confirm the same synthetic profile and Tracker rows
      survive. Confirm the API rejects unsigned `/v2` calls in production.
- [ ] Record the actual public URL, tested commit, model used and validation results.
      A deployment that only renders its Home page has not passed the product journey.

## 2. Backup, restore and rollback

The user-facing **Career Profile → Your data → Download my data** exports a ZIP through
`GET /v2/account/export`. It copies files directly, including SQLite files, and is not
an atomic whole-workspace backup while requests or batches are writing. There is no
restore/import-archive endpoint. Use an operator restore rehearsal before relying on it.

- [ ] First rehearse on a synthetic workspace in an explicit scratch data directory.
      Record expected profile version, saved jobs, review count and application count.
- [ ] For a consistent operator archive, stop accepting requests and finish/stop batch
      writers; close the API and any Streamlit process sharing the directory. Archive
      the resolved data directory, including `/data/users`, resume versions, artifacts,
      reviews, batch state and all database sidecar files. If writers must remain live,
      use SQLite's backup API for databases plus a coordinated file snapshot instead
      of copying an active `.db` alone. See [SQLite backup guidance](https://sqlite.org/backup.html).
- [ ] Store encrypted backups outside the repository, with restricted access and a
      retention/deletion policy. They contain personal data and may contain encrypted
      Gmail refresh tokens. Store the needed secret separately in the secret manager.
- [ ] Restore into a new empty scratch directory with writers stopped. Point an isolated
      server's `JOB_COPILOT_DATA_DIR` there; do not overwrite the builder's real folders.
      Verify database integrity, profile/version, saved jobs, reviews, downloads and
      Tracker counts, then exercise continuing an interrupted batch.
- [ ] Rehearse application rollback using the last tested commit and compatible data;
      do not assume restoring code restores data. Preserve the failed deployment's
      data before any production restore. Record time to recover and missing changes.
- [ ] Treat Render disk snapshots as an additional recovery mechanism, not the sole
      database backup. Restoring a snapshot overwrites the entire disk and loses later
      changes; Render warns against using raw disk restores for custom database
      recovery. See [Render persistent disks](https://render.com/docs/disks).
- [ ] Plan secret rotation: `AUTH_SECRET` changes invalidate web sessions;
      `WORKSPACE_TOKEN_SECRET` changes must be coordinated across API/web and also change
      the encryption key for stored `gmail.json` refresh tokens. Disconnect/reconnect
      Gmail or perform an explicitly designed migration; do not silently discard them.

## 3. Google sign-in and Gmail: a real account check

- [ ] In Google Cloud, use a Web application OAuth client. For the initial external
      test, set Audience/publishing status to **Testing** and list participating test
      accounts. Keep account identifiers out of committed research notes.
- [ ] Sign-in scopes are `openid email profile`. Add the actual web origin and exact
      redirect `<web-origin>/api/auth/callback/google`; local default is
      `http://localhost:3000/api/auth/callback/google`. Ports and schemes must match.
- [ ] For optional Gmail, enable the Gmail API, add
      `https://www.googleapis.com/auth/gmail.readonly` to consent-screen data access,
      and register `<web-origin>/api/gmail/callback` (on the web host, not API host).
      Add local callback separately if needed. Set API Google variables as above.
- [ ] Complete sign-in with two accounts; test sign-out, **Sign out on every device**
      across two sessions, and that an unsigned visitor cannot load private data.
- [ ] In Tracker, choose **Connect Gmail**. Verify consent is separate from sign-in.
      Decline once and confirm ordinary Tracker remains usable, then reconnect with
      an allowed test account and grant read-only access.
- [ ] Use an account-controlled mailbox and an existing matching ATS notification to
      run **Check Gmail now**. Do not forge a sender/domain or send email for this check.
      If no matching notification exists, record the empty scan as verified and the
      matching-suggestion case as untested. The current query covers selected ATS
      senders in the last 30 days, at most 25 messages, and has no pagination.
- [ ] Confirm scanning changes no application status. Inspect a suggestion and its
      matching role, dismiss one, confirm another only if accurate, scan again, and
      check history/dismissal persistence. Keep subject lines/mailbox content out of git.
- [ ] Choose **Disconnect Gmail**; verify disconnected UI and reconnect behavior.
      The code attempts Google revocation but tolerates network failure; verify the
      Google account's connected-app access is actually removed for the live case.
- [ ] Test expired/revoked access and readable reconnect instructions. External Testing
      refresh tokens for Gmail expire after seven days. This exception does not apply
      to a client requesting only basic identity scopes. See [Google token expiry](https://developers.google.com/identity/protocols/oauth2).
- [ ] Keep the initial Gmail rollout invite-only. `gmail.readonly` is a restricted
      scope: determine the applicable verification/assessment requirements before
      a broader public rollout; merely switching to **In production** does not complete
      verification. See [Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes)
      and [restricted-scope verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification).

## 4. Browser helper and Chrome Web Store

- [ ] Build with the existing product Python environment:
      `product/.venv/Scripts/python.exe extension/build.py`. Expected package from
      current manifest: `dist/job-copilot-helper-0.2.0.zip`. Record actual version and
      package checksum. Inspect ZIP entries: manifest, popup, match/fill scripts and
      icons; no tests, credentials, resumes or research records.
- [ ] Load `extension/` unpacked in a real Chrome test profile. Use the synthetic
      fixture `extension/test/fixture.html` and a synthetic application kit first.
      Verify Save kit, Fill this page, resume attachment, preserved prefilled fields,
      unanswered required fields, and **Forget my kit**. Confirm no submit event or
      submit-button activation occurs.
- [ ] Check optional embedded-form permission request/denial/grant on each claimed
      host family. Confirm unsupported pages/CAPTCHAs and voluntary demographic
      questions are left alone. A normal-page Playwright test of `fill.js` is not
      evidence that the extension loaded successfully in Chrome.
- [ ] If a person checks a live employer page, use their own intended application,
      keep their data outside repo/test fixtures, and stop before submission. Record
      only anonymized platform, browser/version, field behavior and limitations.
- [ ] Confirm an existing Chrome Web Store developer account, required account setup
      and a reachable public privacy URL `<web-origin>/privacy`. No registration or
      legal certification is implied by an agent test.
- [ ] Prepare two synthetic 1280×800 screenshots, 128px icon, listing text and current
      package from `extension/STORE.md`. Review every capability claim against the
      actual tests before uploading; remove claims not demonstrated on a live site.
- [ ] Check dashboard data categories against the resume, approved answers, stored
      kit and form/page handling; do not automatically copy the draft's "PII only"
      selection. Explain `activeTab`, `scripting`, `storage` and each optional ATS
      host permission. Privacy disclosures and the public policy must agree.
- [ ] Submit for review only using the account owner's accurate declarations; use
      deferred publishing if appropriate and record the actual review outcome.
      See [Chrome publishing](https://developer.chrome.com/docs/webstore/publish) and
      [privacy fields](https://developer.chrome.com/docs/webstore/cws-dashboard-privacy).

## 5. Manual screen-reader pass

Use an experienced tester with NVDA + Chrome/Firefox on Windows, or VoiceOver + Safari
on macOS. Record operating system, browser and screen-reader versions, build/commit,
and anonymous tester ID. Use synthetic data; silence from an automated checker is not
a manual pass. W3C's [Easy Checks](https://www.w3.org/WAI/test-evaluate/preliminary/)
is a starting point, not a full conformance claim.

1. With keyboard only, reach the skip link, navigation, main landmark and meaningful
   headings on all six destinations and Privacy. Verify page title, current-page
   announcement, logical focus order, visible focus and no traps.
2. Import and confirm the synthetic Career Profile. Hear labels, required state,
   field hints and errors; correct an error without losing context.
3. Search Jobs, change filters, open/save a role, select a batch and navigate away.
   Hear loading/results/empty/failure states and selection; return and understand
   progress and completed/failed items without excessive repeated announcements.
4. In Tailor, distinguish original/proposed text and evidence gaps; accept, reject
   and manually edit a section. Hear the outcome of rebuild and validation errors.
   Edit the profile and identify the stale warning and blocked Prepare reason.
5. On Apply, identify the correct job/resume download, helper instructions and
   tracking action. Confirm the UI clearly leaves employer submission to the person.
6. In Tracker, navigate status/history, pasted-email review and optional Gmail
   suggestion; identify required match selection and the confirmation outcome.
7. Repeat key tasks at 200% zoom and phone-sized width. Record exact control/task
   blockers, reproduction steps, expected announcement, actual announcement and
   severity; retest fixes with the same setup.

## 6. Study protocol: two or three independent people

Current human evidence must remain **0 participants** until real sessions happen.
Agent simulations are useful walkthroughs and must be labelled separately. Do not
invent participants, quotes, satisfaction ratings, task times or approvals.

- [ ] Recruit 2–3 job seekers outside the builder, including a first-time user; include
      a keyboard/screen-reader user if available. Use anonymous IDs `P01`–`P03` in repo.
      Keep invitation contacts privately outside git. Explain consent, recording and
      withdrawal; record only what was actually agreed.
- [ ] Run 25–35 minutes per person using fresh scratch workspaces and the supplied
      synthetic resume. Use a model-enabled build; state any stubs or unavailable
      integration before interpreting results. Do not collect their real resume.
- [ ] Give outcome tasks without teaching the clicks: confirm facts; find/save one
      suitable role and add a board; tailor/review/download; edit the profile and
      recover the stale resume; prepare and track; review a pasted synthetic update.
      Stop before any employer submission. Run the batch task if time permits.
- [ ] Ask the person to think aloud. Intervene only after a recorded stuck point;
      distinguish independent completion, completion with help, failure and skipped.
      Record duration, misclicks, first confusion and recovery for each task.
- [ ] Ask: "What would you do next?", "Which changes can you trust and why?", "What
      will this tool do when you prepare an application?", and "What would stop you
      using it again?" If comparing both frontends, alternate their order and use
      different but similar synthetic roles to reduce learning effects.
- [ ] Write one anonymized record per session in `discovery/interviews/` with commit,
      environment, task observations and actual quotes only if consented. Use this
      row format: `ID | task | outcome | seconds | help | observed issue | evidence`.
- [ ] Combine recurring issues, severity and proposed fixes in an experiment record.
      Prioritize any unsafe/incorrect result or inability to finish before cosmetic
      feedback. Retest blockers with a person before calling them resolved for users.
- [ ] Finish Sprint 2 review with actual test results and participant counts. Keep
      automated verification, agent walkthroughs and independent user feedback distinct.

## Evidence and outstanding access

This checklist was checked against `render.yaml`, `apps/api/Dockerfile`, workspace
identity/config/account/Gmail routes, web auth/Gmail routes, `extension/manifest.json`,
`extension/build.py`, `extension/README.md`, `extension/STORE.md`, and spec 009.
Provider facts were checked against the official linked documentation on 2026-10-11.
No account was created, no paid resource bought, no mailbox accessed, no employer
application submitted, and no human research performed by preparing this file.

Live completion needs the actual hosting/OAuth configuration, allowed test accounts,
Chrome developer account and runtime test, screen-reader tester, and 2–3 participants.
Resolve these with the account owner or participants when available; an agent's
approval cannot create consent or independent human evidence.
