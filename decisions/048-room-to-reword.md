# Decision 048: Room to reword: the checks stop blocking ordinary rephrasing

**Date:** 2026-10-13
**Status:** Active. The builder approved all four parts. Reverses part of decision 027 (the 15%
length cap) and narrows two checks from decisions 008/009 and 032.

## Context

Tailoring proposed only tiny rewrites. On the anonymized fixture, 6 of 8 sensible rewrites were
refused by three code-level checks:

1. **Length cap:** a Word bullet could grow by only 15%, which is one or two words.
2. **Semantic drift:** every content word before the first comma, "to" or "by" had to survive,
   filler included. "Built SQL dashboards *used* by 40 managers" couldn't become "dashboards
   *that let* 40 managers".
3. **New words:** any word not already in the profile was refused, even the job's own wording
   for something the requirement review had found evidence for. "cross-team" was refused on a
   bullet about a launch "across 4 teams", for a job asking for "cross-team launches".

The PDF-path instructions also still told the model that "most bullets should end up"
unchanged. Decision 043 allows rewording and reordering (level 1); these checks were blocking
exactly that.

## Decision

1. **Requirement wording is grounded on its own evidence.** A rewrite may use the words of a
   supported requirement on the bullet the review found to be that requirement's evidence
   (`requirement_review.requirement_wording`).
   - **Never borrowed:**
     - named terms the evidence doesn't show;
     - years and numbers ("4+ years" is the job's ask, never the person's claim).
   - **Still checked against the profile itself:** tool names and metrics.
   - **Other bullets:** the same words stay blocked there.
   - **Scope:** both the Word and PDF paths.
2. **Filler may go.** "used", "helped", "assisted", "responsible", "worked", "involved",
   "tasked", "participated", "various", "several", "multiple", "different", "numerous", "duties"
   and "also" no longer have to survive a rewrite. Words that say what was done ("delivery",
   "growth") and every number still do.
3. **The Word length cap is 25%** (was 15%).
   - **First build:** a resume that grows onto an extra page still fails the page check, and
     the decision 022 correction pass shortens grown bullets (or restores them).
   - **Known cost:** after the person has accepted changes, a rebuild that overflows is
     reported but not edited automatically (decision 022). The person may then need to reject
     one long change.
4. **The PDF instructions match the Word ones:** rephrase every bullet whose evidence supports a
   "make clearer" target or required qualification. Conservative mode still overrides this.
5. **A requirement shown "in other words" isn't shown yet** (dogfood round 4). A real run proposed
   nothing, because every target was marked "[already shown; keep it]". Transferable requirements
   ("Collaboration: working cross-functionally…") counted as shown just because their evidence
   bullet was in the resume. Now they count as shown only when the resume names most of what the
   requirement asks for, so naming it becomes the improvement.

6. **PDF resumes get the same treatment as Word** (follow-up, same day):
   - grammar-only rewrites are put back before review;
   - the spec 022 skills (levels 2-3) are added to the skills line by the same code;
   - only the model's own wording on that line is checked;
   - the PDF content check accepts a computed skills line.
7. **Names are never borrowed** (bug hunt round 6, 2026-10-14). Two real holes let an invented
   tool claim pass every check:
   - **The problem:**
     - **Broad word as evidence:** "generative AI and LLM-based tools (Claude Code, Cursor, GitHub
       Copilot) … automated reporting" was direct evidence through the one word "reporting". Its
       whole wording was then the reporting bullet's own, so "…in Python with GitHub Copilot"
       passed.
     - **Product names lent:** "dashboards … in Hex and Mode" lent "Hex" to a dashboards
       bullet.
   - **Now:**
     - a capitalized word or acronym in a requirement is lent only if the bullet already has it;
     - a requirement shown only by one broad word is partly supported and lends nothing (it isn't
       a target);
     - products listed in brackets after "tools"/"platforms" count as named products to check,
       never as evidence;
     - the new-word check also covers short names ("Hex", "AI"); it used to skip every word of 3
       letters or fewer.

## Unchanged

- Never added: employers, titles, dates, degrees, numbers, tools the person never used
  (level 4).
- Every other check stays as it was:
  - unsupported requirement terms;
  - listed-only skills turned into claims;
  - tool scope;
  - the "loyalty" characterization check for words not grounded anywhere.

## Rejected

- **Dropping the new-word check:** it's what stops invented characterizations ("loyalty-focused").
- **Exempting the requirement's words on every bullet:** a bullet that isn't the evidence would
  gain a claim it doesn't show.
- **A bigger cap than 25%:** the correction pass then has to undo more, and reviewed rebuilds
  overflow more often.

## Evidence

`product/tests/test_rewording_room.py`:
- the fixture rewrites that were refused now pass;
- the requirement's words stay blocked on other bullets;
- unshown terms and requirement numbers stay blocked;
- "delivery" and metrics still must survive;
- the 25% cap;
- the PDF instructions.

`product/tests/test_scoped_requirement_evidence.py` (round 6): the GitHub Copilot and "Hex" claims
are refused; a broad word lends nothing; alternatives with "or similar".
