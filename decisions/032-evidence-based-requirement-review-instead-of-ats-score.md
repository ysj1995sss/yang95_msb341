# Decision 032: An evidence-based requirement review instead of an ATS-style score

**Date:** 2026-10-05
**Status:** Active. This implements spec 010. The builder approved the spec and delegated the
open choices.
**Supersedes:** spec 001 step 14 (loop to ≥85% alignment), and the "Already on your resume"
wording from specs 002, 007 and 008.

## Context

Job Copilot's "ATS" features measured keyword overlap but talked about it as if it predicted
employers:

- **Jobs** said a profile term was "on your resume".
- **Tailor** headlined a home-made 60/40 overlap percentage.
- **The free-form path** looped toward 85% of that number.
- **Weak evidence was treated as strong.** A skills-list mention counted as "Direct verified",
  and "likely has this" guesses were sent to the model as "bring into resume".

We checked the builder's four research guides against vendor documentation (spec 010
appendix). There is no universal ATS score or threshold. Greenhouse's matching uses criteria each
hiring team sets, and it doesn't auto-reject. Parsing problems are real.

## Decisions

1. **The requirement review is the guide, not a score** (`analyzers/requirement_review.py`).
   - **Each row:** one required or preferred qualification with one of six statuses: direct,
     transferable, mentioned only, unconfirmed, check yourself, no evidence.
   - **Evidence:** the exact profile passage, with its source and whether it was confirmed.
   - **Shown or not:** whether this resume names it.
   - **Stricter rules than the old analysis:**
     - a named tool needs named evidence (no generic stand-in, no "transferable" credit);
     - an ambiguous acronym (PM, BI, CRM…) needs the same meaning on both sides;
     - facts not yet confirmed never count as evidence;
     - years of experience are left for the person to check;
     - missing hard requirements are listed first.
   - **Rejected: improving the 60/40 score.** Any single number invites chasing. The review
     answers the question that matters: "Does this resume show real evidence for what the job
     needs?"
   - **Rejected: semantic or embedding matching.** It's another dependency and harder to
     explain; the existing competency map and term matcher were enough for the acceptance cases.
2. **The model may only make confirmed evidence clearer.**
   - **What the prompt contains:**
     - "make clearer" targets with their quoted evidence;
     - an explicit do-not-add list.
   - **A code-level guard on both paths** rejects any rewrite that introduces a term the review
     doesn't support, or turns a listed-only skill into a claim. The old fabrication check let
     that through, because the term was in the profile.
   - **Rejected: relying on the prompt alone.** This project has repeatedly found that prompt
     instructions aren't followed reliably (decisions 008 and 009).
3. **No percentage target.**
   - **The free-form loop stops when:**
     - nothing supported is left unshown;
     - a round changes or shows nothing;
     - or after 3 rounds (down from 5).
   - **Unsupported rounds:** a round that adds an unsupported term is discarded.
   - **The overlap number:** still computed and stored (compatibility), shown only under Details
     as "Keyword overlap (Job Copilot's own estimate, not an employer score)".
4. **The readability check is local and honest** (`pdf/readability.py`).
   - **Word path:** the name, email and every bullet must read back from the finished PDF.
     Missing ones fail. Text that reads back broken or out of order warns.
   - **Both paths:** a warning for role order, unknown symbols and non-standard headings.
   - **Label:** "done on this computer, not a check by any employer's ATS". `TEXT_NOT_EXTRACTABLE`
     is unchanged.
   - **The builder's choice:** missing content blocks the download; order problems only warn,
     because two-column layouts read in different orders by different parsers.
5. **The Jobs check reads only Career Profile facts** (not contact details, goals or
   preferences), and says "In your Career Profile".
6. **One explanation and one view for both apps** (`ui/ats_explainer.py`,
   `ui/requirement_review_view.py`). The API serves them, so the web app and Streamlit can't
   drift.
7. **Compatibility.**
   - **Stored data:** enum values and stored fields are unchanged; new fields have defaults.
   - **Older reviews:** a review saved before this change still loads, and gets a review "worked
     out now". It's tested on a real file written by the pre-change code.
   - **APIs:** the `/v2` `alignment` field, the legacy `/tailor` API and `resume_match_score` all
     stay.

## Found by the supervised run (see `discovery/experiments/2026-10-ats-requirement-review.md`)

- **Word bullets:** "List Bullet" style paragraphs weren't read as bullets at all.
- **Degrees:** "BS" didn't count for a bachelor's requirement.
- **"Shown":** the check was too generous to drive any improvement.
- **Codex start-up:** Codex failing to start (Node.js not on PATH) was reported as an empty answer.

All four are fixed, with tests.

## Not done or still open

- **The model's caution:** a cautious model proposes few changes. A stronger model is the
  builder's cost decision.
- **The free-form path end to end:** it ran only with a stubbed model.
- **A person's review:** nobody but the builder has reviewed a real requirement review yet.
  That's still part of the Sprint 2 supervised user tests.
