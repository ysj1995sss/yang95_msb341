# Decision 013: Steps 10-15 audit and rebuild — summary

**Date:** 2026-09-27
**Status:** Active

## Context

A rebuild-and-improve prompt asked for an audit-first pass over Steps 10-15 (job analysis,
benchmarking, gap report, tailoring, optimization, length control) on the premise that the
existing implementation, while functional, might be "brittle, shallow, overly keyword-driven,
duplicated, too conservative, poorly tested, or disconnected from the Career Truth Profile."
Explicit instruction: audit before writing code, reuse existing services, don't rebuild from
scratch, preserve compatibility with Steps 1-9 and 16-24.

The audit (given to the user in full before any implementation started) found the pipeline was
in better shape than the prompt's premise assumed for the DOCX splice path (decisions 008/009
had already added evidence-based gap classification, semantic-drift protection, and a repair
loop there), but found one major structural problem: **two tailoring engines at different
quality levels**. Every decision-008/009 improvement only ever protected DOCX-original uploads
(`DocxBulletTailorer`); a PDF-original upload went through `ResumeTailorer`, an older,
unimproved whole-resume-rewrite path with none of those guardrails. This violated the prompt's
own "prefer ONE tailoring engine" principle, not by design, but by omission.

## Decision

Fixed the audit's findings across six phases, in order, each committed and tested independently:

- **Phase B (Step 10):** Added `JobRequirement`, a structured requirement model
  (`normalized_concept`, `category`, `importance`, `hard_gate`, `source_section`) alongside
  `JobAnalysis`'s existing flat string lists, not replacing them. `normalize_concept()` reuses
  the SAME curated competency vocabulary (`competency_map.py`) the evidence-matching side
  already used, rather than a second synonym table.
- **Phase C (Steps 11-12):** `GapItem` gained an explicit `evidence_level` field (the 5-tier
  DIRECT_VERIFIED/STRONGLY_SUPPORTED/TRANSFERABLE_PARTIAL/WEAK_INFERRED/UNSUPPORTED model) and
  `hard_gate`, sourced from Step 10's `JobRequirement.hard_gate`. `GapReport.unmet_hard_gates`
  gives "a missing hard requirement remains an honest gap" a concrete, queryable answer.
- **Phase D (Step 13 parity):** Consolidated `DiffGenerator.generate_diff` (the freeform path's
  validation) onto the same per-pair semantic-drift/fabrication checks `DocxBulletTailorer`
  already used, and ported the same evidence-first framing and SEMANTIC PRESERVATION prompt
  guidance into `ResumeTailorer`'s system prompt. Closes the two-engines gap for validation and
  generation.
- **Phase E (Step 14):** A bounded (at most one extra) resume-wide optimization pass for the
  DOCX path: when a first tailoring pass looks shallow AND specific high-evidence requirements
  are still unrepresented, one more `tailor_bullets()` call runs with those requirements named
  explicitly, building on the first pass's output rather than reverting it.
- **Phase F (Step 15):** `bullet_length_delta` -- which existed but had zero callers anywhere in
  the codebase -- wired into the freeform path's validation, plus explicit bullet-length
  guidance added to both freeform system prompts. Moved to `utils/length_check.py` to avoid a
  circular import (`diff_generator.py` is imported by `docx_bullet_tailorer.py`, which is
  imported by `docx_export/pipeline.py`, which the `docx_export` package loads at import time).
- **Phase G:** Live regression test against a real posting and the user's real resume (below).

Each phase surfaced at least one real, previously-undetected bug along the way -- not just the
planned improvement -- documented in that phase's own commit message: a years-of-experience
hard-gate regex too strict for realistic phrasing, a first-match-wins competency-matching bug,
a false-positive from a generic shared word ("experience"), Category D being structurally
unreachable (nothing ever classified a preferred-only qualification), and a message-key
collision that double-reported the same fabricated term.

## Phase G: live regression result

Real Airbnb "2027 Global Marketing Development Program Associate" posting, the user's real
resume, through the full updated Steps 10-15 pipeline:

| Metric | Before this session | After |
|---|---|---|
| Original resume match | 12% (session start) | 56% |
| Tailored resume match | (regressed below original) | 60% |
| Bullets changed | 0-3 (typical) | 5 of 15 |
| Bullets rejected by a safety check | -- | 0 |
| Unsupported claims added | -- | 0 |
| Fabrication risk flags | -- | 1 (correctly caught by the newly-consolidated check; not present before this phase's work) |

The one fabrication-risk flag is itself evidence the Phase D consolidation works as intended:
`generate_diff` (called on the final output for both tailoring paths) caught an unearned
"project" characterization that `DocxBulletTailorer`'s own validation had let through on that
specific bullet -- a second, independent layer catching what the first missed, surfaced to the
user for review rather than silently shipped.

## Definition of done, against the prompt's own checklist

1. Job requirements structured accurately -- yes (Phase B), though extraction itself is still
   regex/heuristic, not LLM-based (see below).
2. Required vs preferred vs hard eligibility distinguished -- yes (`hard_gate`, Phase B/C).
3. Benchmarking uses the Career Truth Profile -- yes, pre-existing (decision 009) and unchanged.
4. Exact keyword absence != unsupported -- yes, pre-existing (decision 009).
5. Gap classifications evidence-backed -- yes, pre-existing + `evidence_level` now explicit.
6. Truly missing requirements remain missing -- yes; `unmet_hard_gates` makes this queryable.
7. Tailoring makes meaningful, safe changes -- yes, verified live (Phase G: 5/15 bullets, 0%
   unsupported claims).
8. Safe transferable evidence surfaced -- yes, pre-existing (decision 009).
9. Unsafe factual upgrades rejected -- yes, pre-existing + Phase D extends this to the freeform
   path.
10. Rejected rewrites get bounded repair -- yes for the DOCX path (pre-existing); the freeform
    path has no per-bullet repair loop (see below).
11. Optimization works across the whole resume -- yes for the DOCX path (Phase E, new); the
    freeform path already had a real iterative loop (pre-existing).
12. ATS alignment improves without keyword stuffing -- yes, verified live.
13. Length stays close to original -- yes, DOCX path had a hard cap already; freeform path now
    has a soft warning (Phase F) but no hard enforcement mechanism (see below).
14. Important bullets never silently dropped -- yes; the DOCX splice architecture makes this
    structurally impossible (decision 006), unchanged.
15. Steps 1-9 still work -- yes, verified (this session's earlier PR #2 reconciliation work,
    unrelated to this initiative, also still green).
16. Steps 16-24 can consume the output cleanly -- yes; every change was additive to existing
    dataclasses, no downstream consumer's contract changed.
17. Real-world testing succeeded -- yes (Phase G, above).

548/548 tests passing throughout (started at 519, net +29 across all six phases).

## Known limitations, stated honestly

- **Step 10 extraction is still regex/heuristic, not LLM-based.** The prompt's own docstring
  already says "future versions will use Claude API for more nuanced analysis" -- still true.
  `normalize_concept()`/`hard_gate` detection improve what's built on TOP of the extracted
  requirements; they don't make extraction itself smarter at finding requirements a rigid regex
  misses entirely (unusual section headings, requirements embedded in prose without any bullet
  structure at all, non-English postings).
- **The freeform/PDF path has no repair loop.** Its whole-resume-rewrite architecture has no
  clean per-bullet retry boundary the way the DOCX splice path does (paragraph_index). A rejected
  freeform rewrite currently has no bounded "try again with this specific fix" mechanism.
- **The freeform path's length control is a soft warning, not a hard gate.** The DOCX path can
  verify page count exactly via the docx2pdf round-trip; the freeform path only warns when a
  bullet grew, with no equivalent hard verification step.
- **Step 11's full eligibility/core/preferred/evidence-confidence SCORE breakdown was not
  built** as a new top-level score (decision 009 already scoped this out as low value relative
  to effort; the STRUCTURED DATA a future breakdown would need -- `hard_gate`,
  `evidence_level`, `unmet_hard_gates` -- now exists, so building that view later doesn't require
  re-deriving it).
- **`_HARD_GATE_PATTERNS` and `_GENERIC_FILLER_TERMS` are curated, not exhaustive**, same caveat
  as the existing `COMPETENCY_EVIDENCE_PATTERNS` table (decision 009): extend by adding real
  cases found in live testing, not by loosening the matching logic.

## What would change our mind

If live usage shows the freeform path's lack of a repair loop or hard length gate causing real
user-visible problems (not just a theoretical gap), build one -- the DOCX path's existing
mechanisms are the template, not a novel design needed from scratch. If Step 10's regex
extraction keeps missing real requirements on new postings, that's the strongest signal for
finally building the LLM-based extraction path the original docstring always said was coming.
