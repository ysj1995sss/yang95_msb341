# Decision 047: "Match" is the share of a job's requirements your facts show

**Date:** 2026-10-13
**Status:** Active. Replaces the cf-v2 Candidate fit number everywhere it was shown. Refines
decision 032 (see below).

## Context

The builder found that Candidate fit gave almost every job 85–96%. A profile that showed 1 of
10 requirements still looked like a strong fit. They asked for the number to mean what it says:
"If you only match 10% on the ATS with the job description, it should only show 10%."

The cf-v2 scorer (`job_search/candidate_fit.py`) mixed four parts:
- eligibility;
- core skills from a fixed list of technical words;
- preferred skills;
- "evidence confidence".

Eligibility and evidence confidence were high for most profiles, so they lifted every job. Its
skill list also didn't match the requirement review that the Jobs and Tailor screens show beside
the number, so the two disagreed.

## Decision

1. **Match is worked out from the requirement review** (`job_search/requirement_match.py`), so
   the number and the requirement-by-requirement list agree.
   - **Credit per requirement:**
     - direct evidence: 1;
     - related experience in other words (transferable), or a skill only listed: ½;
     - partly supported: the share of its named terms shown (½ when only the general capability is shown);
     - facts not yet confirmed, or no evidence: 0.
   - **Shown only by one broad word:** ½. Example: "healthcare analytics and reporting" from a
     bullet about "reporting workloads".
   - **"Check yourself" rows:**
     - alternative wording or an unknown platform: counted by the skills they name. "SQL … or R
       or Python" with SQL and Python shown gets at least ½.
     - years of experience, or only ambiguous acronyms: not counted.
   - **Work authorization:** not counted. It's eligibility, answered in Career Profile and shown
     with the hard requirements.
   - **Weights:** required requirements count twice as much as preferred ones.
   - **Fallback:** a posting with nothing countable in its requirement list (only years, say)
     is counted on the skills and tools it names.
   - **None:** a posting with nothing countable at all is "Match not assessed".
2. **The label is "Match"**, in Jobs, Tailor and Tracker. The job detail explains it under
   "How the match is counted": the share of the posting's stated requirements your confirmed
   facts show, how each kind of evidence counts, and that it is **not an employer's ATS score**.
   - **Tones:** green from 60%, amber from 30%, red below.
3. **Large searches use two stages.** The full Match takes about 5–40 ms per job. A broad search
   can match about 1,800 jobs, which would take over a minute in one request. Beyond 100 jobs:
   - a quick pass ranks every job by the share of the posting's named terms that the person's
     facts also name (word lookup, about 0.3 ms per job);
   - the top 100 get the full Match and are ordered by it, with the rest after them in quick-pass
     order;
   - every row on the page shown gets its full Match, wherever it sits.

   The "Newest" view sorts by date, so it scores only the page shown. Job analyses are cached
   per posting text, and Matches per profile, confirmed facts and posting.
4. **Older numbers say so.** An application or a Tailor job scored with cf-v2 before this change
   is shown as "(older fit measure)", never relabelled as a Match.
5. **Compatibility.** Match uses the same `FitResult` shape, so snapshots, batch, Apply and
   Tracker keep working. `scoring_version` is `match-v1`. The legacy `/v2/fit` scorer is unchanged.

## Dogfood round 4 (same day)

A real search scored one job 75% from 3 of its 10 requirements: 7 were "check yourself", and one
bullet containing "reporting" counted fully for "healthcare analytics and reporting". The rules
above for broad words and "check yourself" rows came from that run; the job is now 38%. The same
run found that "using analytical tools" and "dev tool companies" were read as unknown products,
and that work authorization was shown as missing when the person simply hadn't answered.

## Follow-up (same day)

- **The job page shows how many requirements the Match counted** ("6 of 8"). Below 4, it adds
  "few, so this number is rough".
- **Tailor's requirement list takes work authorization from the Career Profile answer**, like the
  Jobs page:
  - "You said yes", "You said no" or "Not answered".
  - It's listed as missing only when the answer is no.
  - The review summary no longer counts it as a missing credential.
- **The competency matcher picks the competency a requirement is about.**
  - **Before:** "Communication: … presenting data insights" was "shown" as data analytics by a
    dashboards bullet.
  - **Now:** competencies named earlier in the requirement come first, and the first one with
    evidence wins.
  - **New evidence:** "partnered with … leads" and "collaborated with … teams" count as partial
    cross-functional evidence.

## How this fits decision 032

Decision 032 rejected an ATS-style score, because one number invites chasing and no universal
ATS score exists. This decision keeps both points:

- **It is not a resume score.** Match measures the person's confirmed facts against the
  posting, not the resume's wording. Tailoring can't raise it by adding words. Decision 032's
  guards still stop any rewrite that adds unsupported terms.
- **It never claims to predict an employer.** The label is "Match", not "ATS score", and the
  explanation says it's Job Copilot's reading of the posting.
- **It uses 032's rules.** Facts not yet confirmed count nothing; a listed-only skill isn't
  direct evidence; years are left for the person to check.

## Rejected

- **Keep cf-v2 and rescale it:** its parts still wouldn't match the requirement list shown beside it.
- **Count only direct evidence:** real related experience would count for nothing, which
  understates people changing careers.
- **Full Match for every job in a search:** too slow for one request (Vercel and Cloud Run
  time limits).
- **Call it "ATS score":** promises something no tool can know (decision 032).

## Evidence

- `product/tests/test_requirement_match.py`: 1 of 10 requirements shown ≈ 10%, weights and
  credits, unconfirmed facts, the skills-only fallback, and the quick pass ranking like the full
  Match.
- `product/tests/test_jobs_state.py`: the two-stage order.
- `product/tests/test_tracker_views.py`: older fit measure labelled.
- `apps/api/tests/test_workspace_jobs.py`: the Match label, explanation, and a large search ranked
  by the quick pass with a Match on every row.
