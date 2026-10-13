# Spec 022: Tailoring that visibly does more (change levels 1–3)

**Status:** Approved (2026-10-12) with the recommended answers: a reviewed adjacency list; levels 2–3 on the skills line only; at most 5 additions; manual review proposes them, while AI-assisted review and auto-apply accept levels 2 and 3 automatically and list them.
**Progress (2026-10-13):** steps 1–5 are built for **Word resumes**:
- the measurement;
- the adjacency list and level 2–3 computation;
- the narrow guard exemptions (the gap gate and the final check);
- the skills line, or a "Core Competencies:" line when there is no skills line;
- the review marks and "Added to skills (adjacent)" in the requirement review;
- the level-1 prompt rewrite;
- dropping additions lowest-priority first when they add a page.

**Not built:** free-form (PDF) resumes don't get additions yet. Auto-apply has its own spec.
**Builds on:** decision 043 (levels 1–3 allowed, level 4 never), spec 010 / decision 032
(requirement review), spec 011 / decision 033, decisions 038–041 (truth guards).
**Glossary:** `CONTEXT.md` (Change level, Proposed change, Checks, Sent log).

## Problem and evidence

- **The symptom:** in every real-model run on the synthetic test resume (2026-10-07, 10-11
  and 10-12), tailoring proposed **0 changes**, so the "tailored" resume equalled the original.
  The builder chose, in decision 043, to let tailoring add keywords and adjacent skills.
- **Three layers push toward "change nothing"** (checked in code, 2026-10-12):
  1. **The model's instructions** (`tailorer/docx_bullet_tailorer.py`, `_build_system_prompt`)
     say "most bullets should end up" unchanged, prefer 2–4 rephrased bullets, and forbid
     "skills not listed in the profile".
  2. **Code guards reject rewrites** after the model answers:
     - semantic drift (a dropped word);
     - unverified characterization;
     - `introduced_unsupported`: no evidence, or a listed skill turned into a claim;
     - `introduced_unscoped_tools`: a tool not used in that activity.
  3. **Decision 043 levels 2–3** contradict layer 1 and parts of layer 2.
- **Unknown, so measured first:** how much of "0 changes" is the prompt and how much is the
  guards. The run warnings record each rejection, but nobody has counted them.

## Change levels, mapped to evidence the app already computes

The requirement review (`analyzers/requirement_review.py`) labels each job requirement:
direct, transferable, partial, mention (listed only), unconfirmed, check, or none.

| Level | Meaning (decision 043) | When the app may do it | Where it may appear |
|---|---|---|---|
| 1 | Reword or reorder what the person wrote | The bullet has direct, transferable or partial evidence | Bullets, summary, skills order |
| 2 | Add a skill the person really has but didn't list | The requirement's term has **direct or partial** evidence in their experience, education or certifications, but isn't in their skills line | **The skills line only** |
| 3 | Add an adjacent skill | The requirement's term has **no** evidence, but the person has a listed **adjacent** skill from a reviewed adjacency list (for example SQL → PostgreSQL) | **The skills line only** |
| 4 | Invent something | **Never:** employers, titles, dates, degrees, certifications, numbers, years of experience, or a tool claimed inside a bullet | Nowhere |

**Why levels 2–3 stay on the skills line:** a bullet says what someone *did* at a specific
job. Adding a tool there claims they used it in that job; that's level 4. A skills line only
claims familiarity, which is the honest reading of an adjacent skill.

## Design

1. **Measure first (no behavior change).**
   - **The runs:** run the real model on 3 synthetic resumes × 3 real postings, on scratch
     data.
   - **Recorded per run:** bullets sent, rewrites proposed, rewrites rejected by each guard,
     and the changes shown.
   - **Output:** a short experiment note. If the guards reject most proposals, the prompt
     change alone won't help, and the note says so.
2. **Level 1, less timid.** Rewrite the model instructions:
   - **Remove:** "most bullets should end up unchanged" and the 2–4 bullet preference.
   - **Ask for:** a rephrase of *every* bullet that has direct, transferable or partial
     evidence for a required qualification, using the job's own wording where the evidence
     supports it.
   - **Unchanged:** every guard in layer 2. Level 1 still can't change what happened.
3. **Levels 2–3, added by code, not the model.**
   - **Who decides:** a deterministic step after tailoring computes the additions from the
     requirement review, so the model can't invent them.
   - **The adjacency list:** a small, reviewed file `analyzers/adjacent_skills.py`
     (SQL ↔ PostgreSQL/MySQL/SQL Server, Tableau ↔ Power BI/Looker, Python ↔ pandas, AWS ↔
     Azure/GCP basics, and similar). The builder can read and edit it; an entry goes in only
     when knowing one skill makes the other quick to pick up.
   - **What each addition is:** a `ResumeChange` on the skills line, carrying `level` (2 or 3)
     and the reason ("Your Acme bullet shows Tableau"; "You list SQL; the job asks for
     PostgreSQL").
   - **Cap:** at most 5 additions per resume, highest-priority requirements first, so the
     skills line doesn't become keyword stuffing.
   - **Format:** Word resumes edit the existing skills/competencies paragraph in place, with
     the same splice and length rules as today. Free-form resumes edit the Skills section.
4. **Guards learn about levels 2–3, narrowly.** Only the additions computed in step 3 may pass
   `introduced_unsupported` and the final unsupported-claim check, and only on the skills line.
   Anything else that adds an unevidenced term is still rejected, exactly as today.
5. **Visible everywhere.**
   - **Review:** each addition is a Proposed change marked "Added skill: you have it" (level 2)
     or "Added skill: adjacent" (level 3), with its reason.
   - **Requirement review:** shows the requirement as "added to skills (adjacent)", not as
     evidence.
   - **The Sent log** (auto-apply, later spec) lists them, as decided in Q14.
6. **Final checks unchanged.** Readability, page length and validation still decide whether a
   Tailored resume can be used. An addition that pushes the resume over its page limit is
   dropped (lowest priority first) before the rebuild, and the review says why.

## Questions for the builder

1. **Level 3 source:** a reviewed adjacency list that I write and you can edit (recommended),
   or let the model suggest adjacent skills (more coverage, but a model can invent adjacency)?
2. **Where levels 2–3 appear:** the skills line only (recommended, see above), or also inside
   bullets?
3. **Cap:** at most 5 added skills per resume (recommended), a different number, or no cap?
4. **Defaults:**
   - **Manual review:** levels 2–3 start as *proposed* and the person decides.
   - **AI-assisted review and auto-apply:** level 2 is accepted automatically, and level 3 too,
     because Q14 chose "not asked in advance, listed after". Recommended: as stated. Or should
     level 3 always wait for the person?

## Out of scope

Auto-apply itself (its own spec), changing the requirement-review labels, bullet-level level 2–3
claims, a second model call, or any change to the final checks.

## Tests and verification

- **Unit tests:**
  - level 2 is found from direct evidence;
  - level 3 only comes from the adjacency list;
  - level 4 terms (degrees, certifications, years of experience) are never added;
  - the cap holds;
  - the guards still reject an unevidenced term anywhere except a computed skills-line addition.
- **API and browser:** review shows the level marks; AI-assisted mode follows question 4;
  validation still blocks a failing resume.
- **Live runs:** repeat step 1's 9 runs after the change and report before/after counts of
  changes shown and checks passed, plus a sample of every added skill, for the builder to
  judge. Synthetic data only.
- **Suites:** run them all and report exact counts.

## Plan (small commits; push when the builder asks)

1. The measurement runs and their experiment note.
2. The adjacency list and level 2–3 computation, with unit tests.
3. Narrow guard exceptions, with tests showing unevidenced terms are still blocked elsewhere.
4. Word and free-form skills-line edits, the review marks (API and web), and AI-assisted
   handling.
5. The model-instruction rewrite for level 1.
6. The after-runs, experiment, decision 044, handoffs and the suites.
