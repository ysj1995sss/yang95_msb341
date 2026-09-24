# Decision 008: Evidence-based tailoring quality, enforced in code

**Date:** 2026-09-23
**Status:** Active

## Context

Live testing against a real American Express posting exposed that the DOCX bullet tailorer was
doing shallow keyword substitution rather than evidence-based tailoring: of 15 bullets, only 2
were touched, and one of those two changes was actively wrong -- "front-store growth strategy"
was narrowed to "front-store acquisition strategy" (a real word from elsewhere in the resume,
but the wrong word for THIS bullet's actual claim), and "loyalty" was added to characterize a
program the resume never describes that way, just because "loyalty" appears in the job posting.
The user filed a detailed, structured critique distinguishing several failure modes: shallow
tailoring, inference-as-fact, semantic narrowing, unused existing evidence, and no
self-check on tailoring depth.

## Decision

Fixed each failure mode with a **code-level hard guardrail**, not just a prompt instruction --
consistent with this session's repeated finding that a flaky LLM backend does not reliably follow
prompt-only rules (the system prompt already told the model not to do exactly what it did, twice).

- **Semantic narrowing** (`DiffGenerator.check_semantic_drift`): a rewrite that drops any of the
  original bullet's own content words is rejected outright and reverted, regardless of whether
  the replacement word is itself legitimate elsewhere in the resume. Compares word STEMS (not
  exact strings) so a plain tense/plural change isn't mistaken for dropping the word.
- **Unverified characterization** (`DiffGenerator.check_bullet_pair_fabrication_risk`, generalized):
  previously only checked a fixed list of ~18 tech keywords and numeric metrics -- useless for a
  marketing resume, which is exactly how "loyalty" slipped through undetected the first time.
  Generalized to flag ANY new content word not grounded in the bullet's own original text or
  anywhere else in the verified profile, exempting a curated list of common resume action
  verbs/connectors (a verb synonym is safe rephrasing; a new noun/adjective characterizing the
  accomplishment is not). Promoted from a downstream warning to a hard reject in
  `DocxBulletTailorer._parse_and_validate`, alongside the length cap and semantic-drift checks.
- **Shallow tailoring / unused evidence** (Problem 1/4): rewrote the system prompt to require
  surveying every bullet across every job for existing evidence BEFORE deciding anything needs a
  new phrase, and to prefer rephrasing 2-4 bullets well over touching many superficially. This is
  prompt-only (no code enforcement of "did the model actually look everywhere first" is
  practical), but paired with the self-check below so a shallow pass is at least visible.
- **Competency reprioritization** (Problem 6): `docx_structure.py` now also finds the "Core
  Competencies" line as a splice target, with a reorder-only validation
  (`_split_competency_line`) that hard-rejects any edit whose item set doesn't exactly match the
  original -- items can be reordered by relevance, never added, removed, or reworded.
- **Insufficient-tailoring self-check** (Problem 7): `run_docx_tailoring_pipeline` now counts
  bullets evaluated/changed/rejected and how many gap-report items had real evidence (Category
  A/B/C), and flags `tailoring_seems_shallow` when very few bullets changed despite several
  addressable requirements. Surfaced as a warning, not an automatic retry -- the LLM backend is
  flaky enough that a second blind pass isn't guaranteed to do better, and doubles latency/cost
  on every request.

## What would change our mind

The `_SAFE_REPHRASE_WORDS` exemption list is a heuristic, not exhaustive -- if real usage shows
a common verb slipping through unexempted (over-rejecting legitimate rephrasing) or a
characterizing noun/adjective sneaking past it (under-catching), the list needs tuning either
direction. If `tailoring_seems_shallow` false-positives often on resumes with genuinely low
JD overlap (as opposed to the tool actually under-using real evidence), the threshold or the
signal itself needs revisiting.
