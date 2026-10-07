# Supervised run: batch polish (spec 014, 2026-10-07)

**Why:** spec 014 requires a real batch with the real model:

1. restart the API mid-batch and continue it;
2. edit the profile and see the out-of-date warnings;
3. tailor again.

**Setup:**

- **Server:** the local workspace API (`run_local.py --codex`), using a **scratch data folder**,
  the synthetic test resume (`apps/web/e2e/fixtures/resume.docx`) and real job boards.
- **Model:** `codex-cli` (the builder's ChatGPT plan), as in earlier supervised runs.
- **How it was driven:** through the `/v2` API that the web page calls. The web interface itself
  is covered by the Playwright case "batch polish: out-of-date jobs, tailor again, and
  continuing a stopped batch".

## 1. Restart mid-batch, then continue

| Time | What happened |
|---|---|
| 10:00:45 | Started a batch of 3 real postings: Lyft "Data Analyst, Go-To-Market Sales Insights", Lyft "Data Analyst, People Analytics", Cursor "Data Analyst, User Operations". |
| 10:01:21 | Job 1 done (about 35 s); job 2 running. **The API was stopped and started again.** |
| 10:01:34 | `GET /v2/batch`: "stopped", "1 of 3 tailored", 2 can be continued, with the note "This batch stopped before it finished (the app restarted)…". Jobs 2–3 were "Not started", and the run status was idle. Detected at once, because the batch records its process and that process had exited. |
| 10:01:42 | `POST /v2/batch/continue`: only jobs 2 and 3 ran. Job 1 wasn't redone. |
| 10:02:44 | "3 of 3 tailored", 0 left to continue, with the batch's own options. |

## 2. Edit the profile, and the warnings

- **The change:** the Career Profile summary was edited.
- **The batch list:** all three jobs showed `stale: true` with "Your Career Profile changed
  after this was tailored (Oct 7). Tailor it again to use your current profile."
- **Tailor:** with a batch job open, it showed the same message.
- **Prepare reviewed jobs for applying:** all three came back "tailor_again" ("…Tailor it again
  first."), and **nothing was tracked**.

## 3. Tailor again

- **First version:** `POST /v2/batch/again` re-ran the Lyft GTM job on the current profile; it
  was no longer flagged, and preparing it tracked it as "Ready to apply" (nothing submitted).
- **Problem found:** that first version replaced the batch with a one-job batch, so the other
  two out-of-date jobs disappeared from the batch list along with their Tailor again buttons.
- **Fixed (commit `ef576dc`):** Tailor again now redoes the job **inside** the batch.
- **Re-checked live with a new 2-job batch:** after a profile edit both were flagged. After
  Tailor again on one: "2 of 2 tailored", People Analytics not flagged, User Operations still
  flagged.

## Found and fixed during the build (before this run)

- **The heartbeat alone was too slow to detect a restart.** A restarted batch would have kept
  showing "Tailoring now…" for up to 3 minutes. Batches now record their computer and process
  id, and are stopped at once when that process has exited (commit `c63abcc`). The heartbeat
  remains the check for a process on another computer.

## Notes

- **The model made 0 changes on the opened Lyft review.** That's the known careful behavior
  (decision 033), not spec 014.
- **The Streamlit background batch** was verified with AppTest (stubbed model): the click
  returns at once, the batch finishes in the background, and a new session sees it. It wasn't
  run with the real model in the browser.
