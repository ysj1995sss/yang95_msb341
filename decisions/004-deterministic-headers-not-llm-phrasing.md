# Decision 004: Reconcile resume headers against the profile, not the LLM's phrasing

**Date:** 2026-09-22
**Status:** Active

## Context

Three rounds of real-user testing against the same resume all hit variations of the same
problem: the LLM phrases job/education header lines differently on essentially every call --
"Employer | Location Dates" one time, "Title at Employer" the next, "Degree from Institution
(Year)" another -- and each new phrasing broke whatever PDF-layout heuristic had been tuned to
detect the previous one. Each fix (decisions 003, and the follow-up in the same session) patched
the heuristic to catch one more pattern, and each time a new pattern showed up.

Studying [jddavenportOpen/recruit-copilot](https://github.com/jddavenportOpen/recruit-copilot), a
reference implementation solving the same problem, showed why: its renderer works from
structured JSON (`job.company`, `job.title`, `job.dates`) and never parses freeform LLM text for
layout at all. Headers are simply never at the mercy of how the model chooses to phrase things.

## Options considered

1. **Keep patching the heuristic for each new phrasing.** Rejected: proven three times in one
   session to be a losing game against an LLM's non-deterministic formatting choices.
2. **Rewrite the tailoring pipeline to return fully structured data** (per-job bullet lists keyed
   to the profile, matching the reference implementation's architecture exactly). The more
   thorough fix, but a large change: it touches the optimizer's iterative refinement loop, the
   diff generator, the API response schema, and the Streamlit UI, all of which currently consume
   a single resume-text string.
3. **Reconcile headers against the profile as a post-processing step**, without changing the
   tailor()/optimize() public interface. Detect each job/education entry's header+bullets block
   by position (a block boundary is any non-bullet line following a run of bullets), and replace
   only the header lines with ones built directly from the verified profile -- keeping the LLM's
   bullet text as-is.

## Decision

Went with option 3. It captures the reference implementation's actual insight -- headers must
never depend on how the LLM phrases things -- without the blast radius of option 2. Matching
blocks to profile entries by position only proceeds when the block count matches the profile's
entry count exactly; a mismatch (the LLM merged or dropped an entry) falls back to leaving that
section untouched, which is safer than guessing a wrong pairing. This also closes a subtler gap
option 1 never addressed: nothing previously enforced that the LLM's own header text stayed
byte-identical to the verified employer name and dates, rather than a paraphrase of them --
reconciliation guarantees that too.

Live-verified against the real resume/job that exposed all three phrasing variants: every job and
degree entry now renders with the exact same canonical format, regardless of how the LLM phrased
its output that call.

## What would change our mind

If block-count mismatches turn out to be common in practice (the LLM frequently merging or
splitting entries), the position-based fallback would leave too many sections unreconciled to be
useful, and option 2's fuller structured-data rewrite would become worth its cost.
