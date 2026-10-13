# Decision 043: Product direction (auto-apply, relaxed tailoring rule, online, retire Streamlit)

**Date:** 2026-10-12
**Status:** Direction set by the builder in a planning interview. **Nothing here is built yet.**
Each item needs its own spec, approved before work starts.
**Supersedes in part:** decision 016 (never submit) and the "evidence-only" tailoring rule of
decision 032, as stated below.

## Decisions

1. **Audience:** job seekers in general.
2. **Done means:** 3 real job seekers each finish search → tailor → apply in one sitting without
   the builder's help, and each says they'd use it again. Agent walkthroughs don't count.
3. **Auto-apply replaces "never submit".**
   - The app applies on its own, with no per-application check. The person may choose to review
     each resume, or each application, before it is sent.
   - **Guardrails (accepted):** only send a resume that passed every check; a daily cap, starting
     at 10; a pause button; a log of everything sent.
   - **Added items:** keywords and adjacent skills added by the app are not asked about in
     advance but are listed in the log after sending. The person can opt in to seeing them
     before sending.
   - **Starts on one platform** (Greenhouse, Lever, Ashby or SmartRecruiters), supervised by the
     builder, chosen after checking which employer form is simplest.
4. **Tailoring may add** (1) rewording and reordering, (2) keywords for skills the person really
   has but didn't list, and (3) adjacent skills. **It never invents** employers, titles, dates,
   degrees, numbers or tools the person never used (level 4). The builder chose levels 1–3.
5. **Online, free budget, sign-in required.** The first online version is only for the 3 testers;
   it opens wider once it is stable and the privacy checks are done. No account is touched
   without the builder's explicit OK, and a deployment spec comes first.
6. **The website (`apps/web`) is the product. Streamlit is retired now:** it gets no new work.
   Removing it is a separate, specced step; the old UI stays recoverable at the tag
   `ui-streamlit-v1`.

## Known risks (recorded so they aren't forgotten)

- **Auto-apply is irreversible per submission.** Employer forms have bot checks, login walls and
  custom questions, and some employers' terms forbid automated applications. Expect failures that
  need the person. The one-platform pilot exists to find out how many.
- **Levels 2–3 sent without prior sight** can put a claim in front of an employer that the person
  never saw. The log and the opt-in preview are the mitigation; level 3 is the riskiest.
- **Free hosting** usually sleeps and may lose files, and resumes are private data.

## Rejected

- Auto-apply on all four platforms at once; the first version has one.
- Level 4 (invented claims): it can get an offer withdrawn, and it harms the people the product serves.
