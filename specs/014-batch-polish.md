# Spec 014: Batch polish — resume, out-of-date warnings, and a non-blocking Streamlit batch

**Status:** Implemented and locally verified on 2026-10-07; see decision 036 and `discovery/experiments/2026-10-spec-014-batch-polish.md`. Two changes from this draft: a batch
also records its computer and process id, so a restart is detected at once (not after 3 minutes);
and Tailor again redoes the job inside the existing batch instead of starting a one-job batch.
**Builds on:** spec 011 / decision 033 (batches), decision 016 (never submit).

## Problem and evidence (checked against `main` at `8f32867`)

1. **A stopped batch can't be continued.**
   - `batch_router._read_batch` marks a running batch "stopped" when the server restarted,
     and lists the unfinished jobs as "Not started".
   - The only way forward is to select those jobs again in Jobs and start a new batch.
   - The batch never saved its options (model, length, conservative mode), so they couldn't be
     reused anyway.
   - Jobs that failed, and jobs skipped by "Stop after the current job", have the same dead end.
2. **An out-of-date review looks current.**
   - A saved review (`review_store`, format 2) doesn't record which Career Profile it was
     tailored from.
   - Suppose a person tailors 10 jobs and then fixes a date or removes a skill in their
     profile. Every saved review and resume still looks ready, and "Prepare reviewed jobs for
     applying" tracks them as "Ready to apply".
   - That's a truthfulness gap: the resume they send may contradict their own corrected
     profile.
3. **The Streamlit batch blocks the page.**
   - `ui/batch_panel.render_batch_runner` tailors every job inside one page run.
   - A batch of 10 at about 60 s each locks the Jobs page for about 10 minutes.
   - Leaving the page stops the batch partway.
   - The list of batch jobs lives only in that browser session (`batch_job_ids`), so Tailor's
     switcher and Apply's prepare forget the batch in a new session.
   - The web app keeps its batch in `users/<owner>/tailor/batch.json`; Streamlit doesn't.
4. **"Restarted" is detected by process id alone** (`BOOT_ID`). If two processes share a data
   folder, for example the API and Streamlit started locally on the same folder, each would
   call the other's running batch "stopped".

## Goal and user workflow

- **After a restart, failures or a stop**, the batch shows **"Continue batch: tailor the 3 jobs
  that didn't finish"**. One click continues with the same options. Jobs already tailored are
  left alone.
- **Profile changes are flagged.** Each tailored job, its Tailor review and its row in Apply's
  prepare results say so when the Career Profile changed after it was tailored: "Your Career
  Profile changed after this was tailored (Oct 6). Tailor it again to use your current
  profile." A **Tailor again** button re-runs just that job.
- **Preparing is held back.** "Prepare reviewed jobs for applying" doesn't mark an out-of-date
  job "Ready to apply"; it says "Tailor again first". The question below asks whether this
  should block or only warn.
- **Streamlit runs batches in the background**, like the web app. The page stays usable, and
  progress refreshes every 2 seconds. Leaving the page doesn't stop the batch. Both apps read
  the same batch file, so Tailor and Apply see the batch in any session, in either app.

Nothing is ever submitted.

## Design

### 1. One batch runner shared by both apps (`product/resume_tailorer/batch_runner.py`, new)

Move the worker loop out of `apps/api/app/workspace/batch_router.py` into the product package,
so the API and Streamlit run the same code.

- **State file:** `batch_runner.read_batch(user_dir)`, `write_batch(...)`, and `view(...)`
  (the summary line). They use the same file and format as today,
  `users/<owner>/tailor/batch.json`, plus additive fields (§2).
- **Starting:** `start_batch(owner_dir, items, options, *, tailor_one, use_limit, on_status)`
  starts a daemon thread. The hooks keep app-specific pieces out:
  - `tailor_one(job_id)` does one job (it wraps `batch.tailor_job`);
  - `use_limit()` raises when the daily tailoring limit is reached; in the API it's
    `limits.use(owner, "tailor")`, and in Streamlit it's a no-op, as today;
  - `on_status(step)` lets the API keep updating its run-status file.
- **One batch at a time per person:** a file lock (`batch.lock`, created with `O_EXCL`, holding
  the process id and a heartbeat) works across processes. The API's in-process `_RUNS_LOCK`
  still guards single runs as today.
- **Stopped batches:** a batch counts as stopped only when its heartbeat is older than 3 minutes.
  The worker writes the heartbeat every 30 s from a small ticker thread, even mid-job. This
  replaces the process-id-only check (problem 4). On detection, the "stopped" state is written
  back to the file, so it sticks.
- **What's rejected:** keeping two loops, one per app. They'd drift, which is spec 011's
  "two frontends" risk.

### 2. Continue a batch

- **Saved options:** `batch.json` gains `options`: model name, length and conservative mode.
  These are the request's choices; keys never go in the file.
- **Resumable items:** each item gains `resumable: bool`. It's true for jobs that are
  "not_started" (restart), "failed", or skipped by "Stop after the current job". It's false for
  jobs skipped because the posting has no description or the daily limit was reached; those
  show their own reason.
- **The API:** `POST /v2/batch/continue` re-queues the resumable items, keeps the finished
  ones, and starts the runner with the saved options.
  - It's refused (409) while any run or batch is running, or when nothing can resume.
  - It needs the Career Profile resume, as starting does.
  - Each re-run job counts toward the daily limit when it starts, as now. A job interrupted
    mid-run counts again; the limit window is per day, so this is rare and stated.
- **Interfaces:**
  - *Web:* `BatchStrip` shows **"Continue batch (N left)"** whenever the batch isn't running
    and N > 0.
  - *Streamlit:* the same button in the batch panel.

### 3. "Your profile changed since this was tailored"

- **Recording the profile version:** `run_tailoring` stores two new keys, used by single runs
  and batch runs alike:
  - `profile_version`: the sha256 of the Career Profile, the same canonical hash as
    `job_service._profile_hash`;
  - `tailored_at`, an ISO time.

  `review_store` keeps encoding plain strings, so the format stays 2. Reviews saved earlier
  load fine and simply have no version.
- **The check:** `batch.review_freshness(state, profile) -> Freshness(stale: bool | None,
  message)`.
  - It returns `None` when the review predates this change; nothing is claimed.
  - It returns `True` when the hashes differ.

  The wording lives in `ui/` so both apps share it.
- **Where it shows:**
  - **The batch list (both apps):** a chip "Profile changed", the message, and **Tailor
    again**. That button runs a one-job batch with the saved options.
  - **The Tailor page**, when a saved review is open (single or batch): an alert above the
    review. It doesn't block reviewing.
  - **Apply's prepare** (`batch.prepare_jobs`): a new outcome, `"tailor_again"`, with the
    message "Your Career Profile changed after this was tailored. Tailor it again first." The
    job isn't tracked. New value; existing values are unchanged.
- **Scope:** any change to the profile counts, including fixing a typo in a bullet. Comparing
  only the facts a resume uses is more precise, but harder to get right. The question below
  covers this.

### 4. Streamlit without blocking

- **Starting:** `render_batch_runner` starts the shared runner, so the page returns
  immediately.
- **Progress:** a `st.fragment(run_every=2)` shows the batch from `batch.json` (status, items,
  Continue, Stop), refreshing only itself. It stops refreshing once the batch isn't running.
- **The Tailor switcher and Apply's prepare** read `batch.json` instead of the session key, so
  they work in a new session. The session key is still accepted as a fallback for a batch
  started before this change.
- **"Stop after the current job"** is added to Streamlit; the web app already has it.

## Compatibility

- **`batch.json` from before this change** has no `options` and no `resumable`. Such a batch can
  still be viewed; Continue uses default options (preserve length, not conservative, the
  server's model) and treats not_started, failed and cancelled-skipped items as resumable.
- **Saved reviews:** format 2 is unchanged and the new keys are additive. The legacy fixture
  `product/tests/fixtures/ats/legacy_review_format2.json` must still load, with no stale
  warning.
- **API fields:** all existing fields stay. New fields: `options` and `resumable_count` on the
  batch, and `resumable` and `stale`/`stale_message` on items.
- **Data:** no schema or database changes.

## Out of scope

- Running several jobs at once (it would spend the model and the daily limit faster); batches
  stay one job at a time.
- Larger batches (still 10).
- Re-tailoring automatically when the profile changes, which would spend money without being
  asked.
- Any submission (decision 016).

## Tests

- **Product:**
  - the runner: start, cancel, a job failing, the limit stopping it, the heartbeat marking a
    batch stopped (with time injected), the file lock refusing a second batch;
  - continuing: which items resume, options reused, a legacy `batch.json`;
  - freshness: a new review, a changed profile, a legacy review with no version;
  - `prepare_jobs`: the `tailor_again` outcome;
  - Streamlit AppTest: starting a batch returns without blocking, the progress fragment shows,
    the switcher works from `batch.json` in a new session.
- **API:** continue (409 cases, happy path); stale fields on items; Tailor's saved-review view
  carries the stale message.
- **Web:** lint and types. A Playwright case:
  - batch two jobs;
  - edit the profile;
  - see "Profile changed" on both;
  - Tailor again on one;
  - prepare: one is "Tailor again first";
  - a stubbed "stopped" batch shows "Continue batch".
- **Supervised run:** one real batch of 2–3 jobs on the local API. Restart the API partway,
  click Continue, then edit the profile and see the warnings. Record it in
  `discovery/experiments/`.

## Implementation plan (small verified commits; push only when the builder asks)

1. `batch_runner.py`: the state file, heartbeat, file lock and loop, with tests. Move the API
   onto it with no behavior change; the API tests stay green.
2. Continue: options, `resumable`, `POST /v2/batch/continue`, with tests.
3. Freshness: `profile_version`/`tailored_at` in `run_tailoring`, `review_freshness`, the
   `prepare_jobs` outcome, and the API fields, with tests, including the legacy fixture.
4. Web: Continue and Tailor again in `BatchStrip`, the stale alert in Tailor, the prepare label,
   and Playwright.
5. Streamlit: the background runner, progress fragment, Continue, Stop, Tailor again, and the
   switcher and prepare reading `batch.json`, with AppTest.
6. Full suites, the supervised run and its record, decision 036, and the handoff docs.

**Files touched:**

- *Product:* `batch_runner.py` (new), `batch.py`, `tailoring_service.py`,
  `ui/batch_panel.py`, `ui/` wording, `pages/5_Tailor.py` and the Apply page.
- *API:* `apps/api/app/workspace/batch_router.py`, `tailor_router.py` (the saved-review
  freshness).
- *Web:* `apps/web/src/components/batch.tsx`, the Tailor page, `lib/types.ts`, `e2e/`.

## Builder's choices (2026-10-06)

| Question | Choice |
|---|---|
| An out-of-date job at "Prepare" | Blocked: "Tailor it again first" |
| What counts as "changed" | Any Career Profile edit |
| The shared runner | Yes: one runner in the product package, used by both apps |
