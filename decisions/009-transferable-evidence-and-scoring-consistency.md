# Decision 009: Transferable-evidence recognition and cross-pipeline scoring consistency

**Date:** 2026-09-23
**Status:** Active

## Context

Live testing against a real "2027 Global Marketing Development Program Associate" posting showed
a 12% baseline match score and zero successful bullet edits -- nearly every attempted rewrite was
rejected by the anti-fabrication safeguards. The user's diagnosis, backed by a detailed spec: the
system was treating "not written with the job description's exact phrase" as "unsupported," even
when the resume contained clear, truthful, transferable evidence (e.g. "led a 10-person team,"
"100% on-time delivery," "risk mitigation," "aligned 30+ cross-functional stakeholders" for a
"project management" requirement). Explicit instruction: do not weaken anti-fabrication
safeguards -- improve evidence retrieval, semantic matching, and rewrite validation instead.

## Decision

**Do not loosen truth standards; add evidence recognition the old lexical matcher structurally
couldn't do.**

- **Curated competency-evidence map** (`analyzers/competency_map.py`): a hand-authored,
  reviewable table mapping abstract competencies (e.g. "project management," "business analysis,"
  "cross-functional leadership") to concrete regex evidence patterns, split into "strong" and
  "partial" confidence tiers. Deliberately curated, not open-ended LLM synonym expansion -- the
  fix request was explicit that unvalidated LLM-proposed mappings must not be trusted. Consulted
  by both `GapAnalyzer._classify_requirement`/`_classify_skill` (STRONG match -> Category B,
  PARTIAL match -> Category C, reusing the existing A-E enum rather than adding new categories)
  and `ResumeBenchmarker._has_qualification` (baseline score), so the two scores stay
  methodologically aligned.
- **Education-status evidence matcher** (`find_education_status_evidence`): found live while
  verifying the above -- a real in-progress MBA graduating 2027 still scored as a total gap
  against "Currently enrolled in an accredited MBA program with an intended graduation of Spring
  2027," because (a) `_profile_to_text` never included `edu.degree`/`field`/`institution`/`year`
  at all (only `.notes`), and (b) even after fixing that, "MBA" is 3 letters and the word-overlap
  ratio filter only considers 4+-letter words (or a fixed tech-acronym allowlist "MBA" isn't in).
  Generic word overlap can't work here -- the requirement is mostly enrollment-status filler
  ("currently," "enrolled," "accredited," "intended," "graduation," "spring") that never appears
  verbatim in any resume. Added a dedicated, narrow matcher: fires only when the requirement text
  names a degree/program/enrollment concept, checks degree-level agreement (MBA/master/bachelor/
  PhD/JD) against `profile.education[*].degree`, and checks any explicit year in the requirement
  against `edu.year`. A wrong degree type or wrong year still correctly fails -- this recognizes
  real matches, it doesn't paper over real gaps.
- **Semantic-drift core/elaboration split** (`diff_generator.check_semantic_drift`): the previous
  check rejected ANY wording change anywhere in a bullet. Split each bullet at its first
  purpose/method/list marker (`to`/`by`/`,`/`;`/`and`); content words before the split are
  strictly protected, words after it can be freely reworded. Metrics/numbers are hard-checked
  independently of clause position (a genuine gap found while building this: the original
  word-based check couldn't see numbers at all, since digits contain no 4+-letter run).
- **Evidence-backed competency labels in bullet text** (`_competency_label_words_evidenced_by`):
  the fabrication check previously flagged "project"/"management" as unverified new words even
  when added to a bullet whose OWN original text already strongly matched the "project
  management" evidence pattern (e.g. "100% on-time delivery" + "risk mitigation"). Naming a
  competency a bullet already demonstrates isn't a new claim -- it's the same fact at a higher
  level of abstraction (fix request's Problem 6). Deliberately narrow: exemption only applies when
  THIS bullet's own text matches a STRONG pattern for that exact competency, not "the candidate
  has this competency somewhere" -- verified live that an unrelated bullet claiming "project
  management" with no such evidence in its own text is still correctly rejected.
- **Bounded repair loop and Core Competencies swap** (already landed earlier this phase, carried
  forward unchanged): on rejection, the model gets the specific rejection reason and one bounded
  retry; the Competencies section allows swapping up to 2 items for ones in a server-computed,
  re-validated `evidence_backed_alternatives` list -- never trusting the model's own claim that
  something is evidence-backed.
- **Cross-pipeline scoring consistency bug, found live while verifying the above**:
  `ResumeBenchmarker.benchmark()` (the ORIGINAL score) was upgraded with the competency map and
  education-status matcher, but `ResumeTailoringOptimizer._score_resume()` (the TAILORED score,
  used by both the freeform and DOCX-splice pipelines) still did literal-word-only qualification
  matching. Live-testing the GMDP posting end-to-end showed the tailored score dropping to 16%
  against a 56% original -- not because tailoring made the resume worse, but because the two
  scores were computed by different methodologies and were never comparable in the first place.
  Fixed by threading `profile` through `_score_resume` (optional, so existing callers without a
  profile still work) and applying the same transferable-evidence + education-status fallback
  there, sourced from the TAILORED text's own sentences (so credit reflects what that specific
  version of the resume conveys) plus the profile's own unchanging education history.

## Verified live (GMDP posting, real resume)

- Baseline match score: 12% (as originally reported) -> 56% after these fixes.
- "Currently enrolled in an accredited MBA program... Spring 2027": Category E ("truly missing")
  -> Category A, with the specific education entry quoted as evidence.
- The three major GMDP requirements (business analysis + cross-functional project management,
  leading cross-functional teams, data-analytics-to-decisions) now classify as Category B with
  specific quoted bullet evidence, instead of falling to E.
- Tailored score now stays consistent with the original (56% -> 56%) instead of falsely
  regressing to 16%.
- 3 of 15 bullets successfully tailored (up from 0 before the competency-label-in-bullets fix),
  1 correctly rejected by two independent guardrails (a fabrication-risk flag on an unearned
  "project management" claim in a bullet that doesn't demonstrate it, and separately a semantic-
  drift flag on a repair attempt that dropped "cross-functional" from the core claim).
- 0 unsupported claims added, 0 fabrication-risk issues in the final output.

## Explicitly scoped out this round

- **Problem 3's full weighted candidate-fit breakdown** (Eligibility Match / Core Competency
  Match / Preferred Qualification Match / Evidence Confidence / Overall Fit as separate reported
  fields): the more surgical fix (recognize transferable evidence at the classification level)
  already resolved the reported symptom -- a 12% floor despite substantial real evidence -- without
  needing a new scoring model to calibrate. Revisit if a future live test shows a *correctly*
  classified gap report still producing a misleadingly low or high single score.
- **Problem 14 (resume-wide optimization pass after per-bullet tailoring)** and **the
  REORDER/PRIORITIZE physical-bullet-reordering part of Problem 9**: consistent with this
  session's earlier decision (006) that physical paragraph reordering is too fragile against the
  current LLM backend's reliability for a DOCX splice pipeline that must never add/remove/reorder
  paragraphs. Revisit if a more capable/consistent LLM backend is adopted.

## What would change our mind

`COMPETENCY_EVIDENCE_PATTERNS` and `_DEGREE_TYPE_RE` are curated, not exhaustive -- if live usage
against a new posting shows a real, truthful competency or degree type that isn't recognized,
extend the table (a normal reviewed code change), not the matching logic's leniency. If the
per-bullet competency-label exemption is ever found to launder an unearned claim through some
bullet that merely happens to share a stray keyword with a strong pattern, narrow the exemption
(e.g. require 2+ strong-pattern hits) rather than removing the capability -- the live test showed
it correctly discriminating between an evidenced bullet and an unrelated one on the same run.
