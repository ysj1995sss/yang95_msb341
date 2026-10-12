# Spec 019: Clear, complete, and efficient tailoring review

**Status:** Design approved; written spec awaiting review (2026-10-12)
**Date:** 2026-10-12
**Builds on:** specs 012 and 016–018; decisions 014, 018, 038–041.
**Evidence:** The builder's 2026-10-12 Tailor screenshot shows 13 review rows with repeated, truncated labels, only one change visible in detail, and a failed artifact. Code inspection shows the queue renders `change.requirement || change.original` with CSS truncation. `_related_gap` can assign the same requirement to multiple distinct edits. No personal resume contents were inspected, so the screenshot alone does not establish duplicate underlying changes.

## Problem and goal

A job seeker cannot reliably tell distinct proposals apart, read all of their text at once, or decide on several together. They also want to choose, before starting, whether to review every proposal personally or let Job Copilot make conservative evidence-based decisions first. The outcome is a review that is faster without implying that a failed artifact or an unsupported claim is safe.

## Scope and interaction

1. Before `Tailor my resume`, show an explicit review-mode choice: **I'll review changes** (default) or **AI-assisted review**. Explain the latter in place: Job Copilot may accept clearly supported wording, keep originals for unsafe proposals, and leave uncertain edits for the person. It does not submit applications or guarantee an ATS result. Changing mode for an existing review requires tailoring again; it must not silently rewrite saved decisions. The chosen mode is stored with the run/review so reloads and both frontends show what happened.
2. Replace the clipped, requirement-only queue label with section, change type, and a short distinctive original → proposed excerpt. Show the full, untruncated original, proposed, job requirement, supporting fact, reason, and check for each item on demand. Offer **Show all changes** so the person can inspect every before/after pair in one scrollable view. Long text wraps; the sticky action area does not obscure it. Indicate reviewed, unresolved, failed-check, and AI-decided states with text as well as color. Retain keyboard and screen-reader access.
3. Add selection checkboxes, select-all-visible/unreviewed, a clear selected count, and **Accept selected** / **Keep originals for selected** actions. Selection never means consent to a hidden or filtered item. Batch decisions are one atomic server operation: validate all IDs belong to the current review, are unique and reviewable, check the review version, then save once; a stale/invalid request changes nothing and returns an actionable error. Manual edits remain per-item. Do not reset existing decisions outside the selection.
4. Diagnose actual duplicate proposals with synthetic reproductions before changing the diff algorithm. The same job requirement can legitimately label many changes; improve the label, not delete those edits. If true duplicates are confirmed, collapse only proposals with the same anchored source occurrence and same original/proposed content, preserving an auditable mapping to saved change IDs. Identical wording at different jobs, paragraphs, or positions stays separate. Do not change decision 018's global matcher or stored IDs solely because rows look similar. Surface any remaining exact repeats as a clearly labeled group rather than silently dropping one.

## AI-assisted decision policy and safety

- Use the existing generated proposal plus deterministic evidence/claim checks; no additional model call, dependency, or model fee is introduced by this mode. Label it **AI-assisted review** and describe the automation honestly, not as independent verification by a second AI.
- Auto-accept only a non-empty, anchored rewrite with an individually passing truth check, an unambiguous source, and no deletion/condensation of substantive information. Auto-keep-original for a proposal that the individual checks fail or that claims a missing requirement. Leave ambiguous pairings, warnings, unsupported/unknown evidence, removals, material condensation, missing source context, and any unclassified case undecided. The person can inspect and override all automatic decisions, subject to the same final safety gates.
- Run the same shared policy for both Next.js and Streamlit; do not implement two divergent truth standards. The mode operates on the saved review's exact source/fact snapshot and must not be applied after that snapshot becomes stale. Record an explanation and origin (`person` or `AI-assisted`) per decided item without changing existing enum values. Older saved reviews remain readable as personal/unknown-origin decisions.
- Neither manual nor AI-assisted batch acceptance bypasses `regenerate` or final artifact validation. Failed artifacts remain unavailable for download and Apply. A failing check cannot be turned into a passing claim merely by marking it accepted. In particular, the screenshot's page-length and missing-metrics failures require correction and a new passing rebuild; batch review alone is not presented as the cure.

## Data flow and compatibility

- Keep `ResumeChange` IDs and the stored disposition vocabulary. Add optional, backwards-compatible run/review metadata for mode and decision origin/reason. Review-version concurrency tokens must be stable across GETs and advance whenever decisions or rebuild state change. The API returns the updated full review after batch decisions.
- Put selection and expanded/all-detail display in the frontend, but put duplicate identity, review eligibility, automatic policy, and batch mutation in shared tested code. API and Streamlit call that shared behavior. Reuse existing per-change decision and regeneration paths; do not introduce a second artifact writer.
- Make failures explicit: no model available, stale review, invalid selection, conflict, save failure, or validation failure. Do not discard a valid prior review on a failed batch decision. No new account, deployment, submission, or push is part of this spec.

## Verification / definition of done

- Synthetic tests reproduce (a) several different edits linked to one requirement and (b) genuinely identical-looking text at different source occurrences. The first is visibly distinct; the second remains separately decidable. A confirmed same-occurrence duplicate is handled without losing a saved decision.
- API tests prove batch decisions are atomic, version-conflict-safe, idempotent where appropriate, and cannot act on blocked/non-reviewable or unknown IDs. Saved reviews reload with decision origin and work across both frontends.
- Policy tests prove safe rewrites are accepted, failed proposals keep the original, and warnings, weak/ambiguous pairings, removals, or unanchored proposals remain undecided. Unsupported project/tool claims and named-platform gaps remain blocked even when a user sends a direct batch request.
- Browser tests cover mode selection before a run, full text in focused and all-changes views, selection/clear/accept/reject, keyboard access, reload, stale conflict, and the failed-artifact gate. Streamlit tests cover the same shared decisions and readable full text.
- Run product and API suites, web lint/types, and browser tests using synthetic scratch data. Do a supervised synthetic browser walkthrough. Report exact counts and any unverified real-model behavior. Preserve the user data folders, `.claude/settings.local.json`, and the unpushed branch.

## Out of scope

No automatic job application, no guarantee of truthful output or ATS ranking, no new LLM adjudicator, no broad rewrite of the free-form pairing algorithm without a reproduced defect, and no promise that the current failed resume can be made valid merely by accepting changes.
