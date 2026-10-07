# Decision 036: One batch runner, continuing batches, and blocking out-of-date resumes

**Date:** 2026-10-07
**Status:** Active. This implements spec 014, which the builder approved with these choices:
block out-of-date jobs at Prepare, count any profile edit, and share one runner.
**Builds on:** decision 033 (batches) and decision 016 (never submit).

## Decisions

1. **One batch runner for both apps** (`resume_tailorer/batch_runner.py`).
   - **What moved:** the loop left `apps/api/app/workspace/batch_router.py`.
   - **Hooks:** the API adds the daily limit and its run status; Streamlit runs batches in a
     background thread. The state file is the same `users/<owner>/tailor/batch.json`, so either
     app sees the other's batch.
   - **Rejected: two loops.** They'd drift, which is the two-frontends risk again.
2. **When a batch counts as stopped.**
   - **Recorded:** a running batch records its computer and process id, plus a heartbeat every
     30 s.
   - **Stopped when:** that process has exited on this computer (detected at once), or the
     heartbeat is older than 3 minutes (another computer). The "stopped" state is written back
     to the file.
   - **Locking:** a short lock file serializes changes across processes.
   - **Rejected: the process-id-only check.** Two processes sharing a data folder each saw the
     other's batch as stopped.
   - **Rejected: the heartbeat alone.** After a restart, the batch looked "running" for up to
     3 minutes; the supervised run would have shown it.
3. **Continue a batch.**
   - **Saved options:** a batch saves its options (model name, length, conservative mode); a
     per-run API key is never stored.
   - **Resumable:** jobs that didn't finish (a restart, a failure, "Stop after the current job",
     or the daily limit) are marked resumable. "Continue batch (N left)" runs only those, with
     the same options.
   - **Limit:** each re-run job counts toward the daily limit when it starts.
4. **Out-of-date reviews.**
   - **Recorded:** a run from the Career Profile records the profile's content hash
     (`profile_version`) and `tailored_at`. These are additive keys, and `review_store`
     stays at format 2.
   - **Flagged:** any later profile edit flags the review in the batch list and in Tailor, in
     both apps.
   - **Blocked:** "Prepare reviewed jobs for applying" refuses it ("tailor_again"), so a resume
     that contradicts the corrected profile can't be tracked as ready by accident.
   - **No claim:** reviews saved before this, and one-off-file runs, claim nothing.
5. **Tailor again** redoes one job inside the existing batch with the batch's options. A job not
   in the batch gets a one-job batch. The supervised run found the first version, which
   replaced the batch and hid the other out-of-date jobs.

## Rejected

- **Comparing only the facts a resume uses.** Fewer warnings, but easy to get subtly wrong; the
  builder chose "any edit" for now.
- **Warning without blocking at Prepare.** Too easy to send an out-of-date resume.
- **Re-tailoring automatically on a profile edit.** It would spend the model and the daily limit
  without being asked.
- **Running jobs in parallel.**

## Evidence

**Tests:**

| Suite | Passed |
|---|---|
| Product | 1,240 (1 skipped) |
| API | 134 |
| Web | lint and types clean |
| Playwright | 22 |

**Supervised run** (`discovery/experiments/2026-10-spec-014-batch-polish.md`):

- an API restart during a real 3-job batch was detected at once, and Continue finished only the
  2 unfinished jobs;
- a profile edit flagged every job and blocked preparing;
- Tailor again cleared the flag for one job and kept the others listed.

## Still open

- **Streamlit with the real model:** its background batch wasn't run with the real model in a
  browser (AppTest only).
- **Process-id reuse:** if a new process reuses the old process id, detection falls back to the
  3-minute heartbeat.
- **Warning precision:** "Any edit" warns even for an edit the resume doesn't use.
