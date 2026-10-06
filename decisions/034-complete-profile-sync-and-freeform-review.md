# Decision 034: Safe Word profile sync and section-level free-form review

**Date:** 2026-10-06
**Status:** Implemented and locally verified under spec 012; CI after push is a separate check.

## Why

Spec 011 proved that a Career Profile bullet edit reached a Word resume, but title, date,
contact, summary, skills and education edits could still leave contradictory text in the
delivered file. The PDF/free-form path reviewed bullets only; a changed summary or skills
line had no independent decision.

## Choice

Keep the person's Word layout. Match roles by exact employer and title first; a changed title
may use a unique employer plus matching dates. A second role at that employer, or an employer
change without a safe identity match, blocks the Word artifact rather than guessing. Education
uses a unique institution or exact degree/field at a repeated institution. If the parser
retains a whole education line as its institution, an unchanged line is accepted as already
represented rather than reparsed into invented fields. Existing contact, summary, labelled or
single-line skills/tools, education and certification paragraphs are rewritten in place. A
missing section is reported but not fabricated.

For the free-form path, identify conventional summary and skills spans before bullet matching.
Only content outside those spans enters the existing global greedy bullet matcher; its
`_compute_changes` algorithm remains unchanged. A changed section gets its own review row and
exact baseline offsets. Rebuilds verify those offsets before replacing text. Old format-2
reviews, which have no offsets, keep their legacy bullet behavior. Unsupported proposed or
manual section claims are blocked even if a person clicks Accept; they can reject or correct
them and rebuild without a new model call. Both UIs label the new rows explicitly.

## Alternatives rejected

- Rebuilding every Word file from profile data would lose the person's chosen layout.
- Global first-match replacement for section decisions could change repeated words in a work
  bullet instead of the summary.
- Auto-inserting absent Word sections or cross-matching two roles at one employer would hide
  uncertainty and risk false claims.
- Treating an accepted unsupported summary as only a warning would let a fabricated duration
  reach Apply; section claims remain a hard failure.

## Evidence and limits

- Synthetic Word tests cover safe and ambiguous roles, title/date/location, contact in the
  body/header, summary, skills/tools, two education entries, certifications, no-op bytes and
  fail-closed tailoring. Synthetic section tests cover wrapped/moved skills, repeated wording,
  independent decisions after format-2 reload and unsupported claims.
- The supervised real-model Word run (existing `codex-cli`, synthetic fixture) passed with no
  findings. Its Word/PDF contained the new title, date, email, summary, skills and education.
- The supervised PDF run blocked a model-written unsupported “4+ years” claim. A separate run
  also exposed an unrecognized `TOOLS & PLATFORMS` boundary; it is now treated as a boundary,
  not part of Skills. Rejecting failing changes rebuilt a PDF with only the expected
  `VISUAL_CHECK_SKIPPED` warning for a generated source.
- A real model did not choose to change the skills line in the final run. Independent skills
  accept/reject/manual behavior is covered by deterministic tests, not claimed as observed live.
- The free provider configured in `.env` was busy; the completed supervised runs used the
  project's existing Codex CLI path. No key, real resume, employer application or submission
  was used.
- The web browser suite reported all 20 cases as passing on a fresh test dataset, but the
  Playwright runner lingered during shutdown on this Windows host and was stopped manually.

The matching rules favor a visible correction over silently handing out an uncertain resume.
If a real template uses headings or layout structures not recognized here, add an anonymized
reproduction before broadening the parser.
