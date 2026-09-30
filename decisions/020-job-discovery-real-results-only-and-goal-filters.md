# 020: Job discovery returns real results only, and goal filters actually filter

**Date:** 2026-09-29
**Status:** Accepted

## Context

A review of Steps 3–9 against live Greenhouse data found four problems:

1. When no real posting matched, the Greenhouse scraper filled the results with generated
   placeholder jobs ("Acme Corp", "Global Enterprises") marked "no sponsorship" and stored them
   next to real jobs. This breaks the product's rule against fabrication.
2. Industry, experience level, and job type were collected on the form but never applied, so a
   search for Healthcare entry-level internships returned the same jobs as an unfiltered one.
3. Only five hardcoded company boards were searched (one of them, Stripe, no longer answers).
4. A search took 45–60 seconds, almost all of it spent re-checking each posting's link one at a
   time with a 1-second gap.

## Decision

- **No placeholder jobs.** Greenhouse returns only real postings. No match means zero results
  with a "no open postings matched" message. If no board can be reached, the search reports a
  failure instead of an empty success.
- **Filters are applied** (`job_search/job_attributes.py`), and every attribute comes from a
  stated fact, never a guess:
  - Industry comes from a curated directory of the 36 companies searched.
  - Experience level and job type come only from explicit words in the title ("Senior",
    "Intern", "Contract"…).
  - Anything not stated is "Not specified" and is kept rather than hidden. The exceptions are
    internship searches, and part-time or contract job-type searches: those roles say so in the
    title, so an unlabeled job is excluded.
  - Every filter accepts multiple choices, and blank means no preference.
- **36 verified company boards** across 10 industries, fetched 6 at a time in parallel.
- **No per-link liveness check for fresh board results.** Greenhouse's board API lists only
  currently published jobs, so a posting fetched seconds ago is already confirmed open. The
  `URLValidator` module stays for re-checking stored jobs later. The search now takes about 10
  seconds.
- Title matching uses the same word-based rule in the scraper and the dashboard. Previously the
  dashboard used a stricter substring match and hid about a third of the stored jobs.
- The company-size field is removed from the form. The MVP prompt lists it as out of scope, and
  it was never applied.

## Rejected

- **Keep placeholder jobs, clearly labeled.** Rejected: they were stored in the same table as
  real jobs and could be triaged and sent to tailoring as if real.
- **Parallelize the link checks.** Rejected: most links share a few hosts, so a polite per-host
  rate limit would still take about 30 seconds, all to confirm what the listing already says.
- **Infer industry or level with an LLM.** Rejected for now: slower, costs money per search, and
  would be a guess where the rule is "never guess".

## Known limitations

- Industry is only known for the 36 directory companies. Other sources show "Not specified".
- Word-based title matching is broad: "Product Manager" also matches "Product Marketing Manager".
- LinkedIn, Indeed, and Handshake are still simulated demo sources. They are labeled in the
  picker, and the page warns when one is selected.

## Update (2026-09-29, after code review)

- **The dashboard shows only jobs from the latest search run.** Each saved posting now records
  `last_seen`, and the page lists only postings seen by the current run. This replaces the
  removed per-link check as the way closed jobs drop out. Postings that aren't returned are not
  deleted: a different title search wouldn't return them anyway, so being absent doesn't prove a
  job is closed. Their triage history is kept.
- **Title matching uses whole words and ignores only filler words** (of, and, the…). "UX
  Designer" now requires "UX", and "Product Manager" no longer matches "Production Manager".
- **Partial outages are reported.** The search summary says, for example, "3 of 36 company
  boards did not respond".
- **No invented fit score.** When a posting states nothing that can be scored, the fit score is
  empty instead of a default 80. The API stores null with the reason "Not enough information".
- **API jobs keep their history across the key change.** A job whose link now keeps its
  identifying `?gh_jid=` is matched to its old record and re-keyed on its next upsert, so its
  triage state carries over.
