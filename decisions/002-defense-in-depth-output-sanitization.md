# Decision 002: Enforce "no commentary in tailored output" with code, not just a prompt instruction

**Date:** 2026-09-21
**Status:** Active

## Context

Live-tested the resume tailoring pipeline against a real LLM (DeepSeek-v4-flash-Free via a
third-party proxy) for the first time. The system prompt already said "Output ONLY the revised
resume content" -- the model ignored it anyway and appended a trailing `**NOTES:**` section
explaining which requirements it didn't add and why. Left unfixed, that commentary would have
been written straight into the generated PDF and handed to a real user as part of their resume.

## Options considered

1. **Tighten the prompt further and hope**: low effort, but this is the same category of fix that
   already failed once -- prompt instructions are not reliably followed by every model, especially
   free-tier/proxy models with looser instruction-following.
2. **Post-process the LLM output to strip commentary, prompt unchanged**: catches the failure
   mode regardless of prompt compliance, but doesn't reduce how often it happens in the first
   place.
3. **Both**: tighten the prompt (reduces how often it happens) and add a code-level strip step
   (catches it when the prompt still gets ignored).

## Decision

Went with option 3. Added `_strip_non_resume_content()` in
`resume_tailorer/tailorer/resume_tailorer.py`, applied to both the initial `tailor()` call and
every `_refine_resume()` call in the optimizer loop, plus an explicit "no notes, no
explanations, no commentary" instruction in both system prompts. Deciding reason: this is
safety-adjacent (bad output reaching a real resume a real person submits), so it gets the same
"don't rely on the LLM behaving" posture as the fabrication guardrails already do -- verified
by re-running the same live scenario after the fix and confirming the commentary no longer
appears, plus 5 new unit tests.

## What would change our mind

If a future model's commentary format doesn't match the "divider + header" or "leading preamble"
patterns this strips (e.g., inline commentary mixed into resume bullets rather than appended at
the end), the strip function would need a different approach -- likely a structured output format
(e.g., asking for JSON with a `resume` field) instead of pattern-matching free text.
