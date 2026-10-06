# Decision 033: Tailor from the Career Profile, batches, a keyword report and per-term evidence

**Date:** 2026-10-05
**Status:** Active. This implements spec 011, which the builder approved ("approve and work on it").
**Builds on:** decision 032 (spec 010).

## Decisions

1. **Tailoring uses the Career Profile; the Word layout is kept by syncing first**
   (`docx_export/profile_sync.py`).
   - **Matching:** roles are matched by employer and title, never by position. The file's bullet
     order is kept, because the profile stores bullets in two lists and has lost their order.
   - **Bullets:** edited bullets are rewritten in place. New ones are cloned from the role's last
     bullet, with the same style and numbering. Removed ones are deleted.
   - **Unmatched roles:** a role only in the profile, or only in the file, is reported.
   - **The session:** keeps the real profile. A file-ordered copy is used only by the bullet
     tailor.
   - **Rejected: rebuilding the Word file from the profile.** It would reshuffle bullets and lose
     the person's layout (decision 006).
   - **Rejected: keeping the re-parse.** Profile edits were ignored, and the review's own advice
     was a dead end.
2. **Per-term statuses and a "partly supported" status.** A requirement naming several tools shows
   each tool's own status. Only evidenced terms are targets; the rest are blocked.
3. **One gap system on every screen.** Jobs' evidence lists and Tailor's missing list come from the
   requirement review. Candidate Fit percentages are unchanged.
4. **Broader, deterministic recognition.**
   - **Vocabulary:** a wider list across fields, with credentials and spelling variants.
   - **Acronyms:** more ambiguous ones (PA, OT, PT, DA, CS, SA, AE…).
   - **Postings without headings:** requirement sentences are found and classified as required or
     preferred by their own wording.
   - **Headings:** sentence-case headings followed by a list are recognized.
   - **Excluded words:** common words that collide with tool names (rest, lean, swift, rust,
     closing, outreach) are left out.
   - **Rejected: model-based extraction.** It costs a call per job, isn't repeatable, and can
     invent requirements.
5. **The model answers every target.**
   - **The rule:** targets carry their requirement id, and each unshown target gets a rewrite or a
     one-line "no safe rewrite" reason. The reasons show in Tailor.
   - **Effort:** Codex runs with "medium" reasoning effort (`LLM_REASONING_EFFORT` overrides).
6. **Readability:**
   - **Two PDF readers** (pypdf and PyMuPDF): a bullet is missing only when both miss it, and a
     disagreement warns.
   - **Word-file checks** (contact only in a header or footer, tables, text boxes) warn.
   - **The free-form path** gets per-bullet checks from its final text.
7. **Batches** (`resume_tailorer/batch.py`, `/v2/batch/*`):
   - **Size:** up to 10 jobs.
   - **Running:** each job runs in a private session, so the open job never changes, one at a time
     under the same run lock and daily limit. Reviews are saved per job.
   - **Preparing:** tracks only reviewed, passing jobs as "Ready to apply". Nothing is submitted
     (decision 016).
   - **Restart:** a batch interrupted by a restart says so.
   - **Streamlit:** runs the queue in the page.
   - **Rejected: a "submit all" button.** Out of scope permanently.

## Found by the supervised runs (`discovery/experiments/2026-10-spec-011-supervised-runs.md`)

- **Degrees:** degree requirements were unactionable targets.
- **Targets:** one target went unanswered.
- **A deleted fact:** the free-form model deleted a true fact to obey the do-not-add wording.

All three are fixed. A summary claiming "4+ years" was caught by the existing unsupported-claim
check.

## Still open

- **Free-form summary edits:** not reviewable as separate changes.
- **Free-form skills-line pairing:** sometimes odd (older behavior).
- **The model is careful:** it makes few changes per run. A stronger model is a cost decision for
  the builder.
- **No real user yet:** no real user has used batches or the keyword report.
