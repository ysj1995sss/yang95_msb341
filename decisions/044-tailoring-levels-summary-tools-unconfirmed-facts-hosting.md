# Decision 044: Tailoring levels 2–3, summary tools, unconfirmed facts, and test hosting

**Date:** 2026-10-12
**Status:** Active.
**Builds on:** spec 022 (approved), decision 043, decision 041 (tool-scope check).
**Evidence:** `discovery/experiments/2026-10-12-spec-022-measurement.md`.

## Decisions

1. **Levels 2–3 are added to the skills line by code** (spec 022, built for Word resumes):
   - level 2 is a skill the person's confirmed experience names;
   - level 3 is a reviewed adjacent skill (`analyzers/adjacent_skills.py`);
   - at most 5, required requirements first, never hard gates, credentials, degrees or years.

   **How they're handled:**
   - The model never edits that line.
   - Manual review shows them as one change, with each skill's level and reason.
   - AI-assisted review accepts them and lists them.
   - On rebuild, only the exact computed additions skip the job-scope check.
2. **Summary tools (builder's answer S1: keep the check).**
   - **The check stays as it is:** decision 041's job-scope check still applies to the summary.
   - **The model is told instead:** both tailoring paths now tell it never to add a tool name to
     the summary.
   - **Rejected: letting the summary name tools that a bullet shows.** It would have fixed the
     PDF failures by loosening the check.
3. **Unconfirmed facts (bug 15; builder's answer S2: warn, with two ways forward).**
   - **The warning:** before a run, Tailor says that facts aren't confirmed and that tailoring
     can't use them.
   - **The two buttons:**
     - "Review and confirm my facts" opens Career Profile;
     - "Use my facts as imported" confirms them in one click.
   - **The risk:** the second button can confirm a fact the importer misread, which today's bug
     hunt showed happens. The builder chose to offer it anyway.
4. **Test hosting (builder's answer H1):**
   - **The setup:** Vercel's free plan for the website, plus Render's free plan for the API.
   - **The limit:** testers' data may be wiped when the free server restarts or sleeps; testers
     are told.
   - **Scope:** this is for the 3 supervised testers only. A deployment spec comes first, and no
     account is touched without the builder's OK.
5. **Writing model provider (builder's answer H2):**
   - **Allowed:** a provider that may train on what it receives, so free tiers are an option.
   - **Recorded risk:** testers' resumes may be used for model training. Testers must be told
     before they upload; the deployment spec and tester instructions will say so.

## Rejected

- **The model inventing adjacency:** a reviewed list is used instead.
- **Level 2–3 claims inside bullets:** a bullet claims use at one job.
- **Auto-confirming facts without asking.**
- **Blocking tailoring until facts are confirmed.**

## Still open

- **The PDF / free-form path** doesn't add skills yet. Its four skills-section checks and the
  whole-text unsupported-claim check need narrow exemptions.
- **Weak evidence matching** in the requirement review: for example, stakeholder management was
  paired with an Excel bullet.
- **Most runs still change little:** 2 of 6 real Word runs added a skill and 1 rephrased a bullet.
