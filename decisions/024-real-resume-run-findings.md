# 024: What the first real end-to-end run found

**Date:** 2026-09-30
**Status:** Accepted; all items below are fixed unless marked open.

The suites were green (813 product tests) when a real DOCX resume, a live SoFi posting and the
configured free model were run through the whole journey. Tailoring silently did nothing.
The causes were all in code that tests using synthetic data could not reach:

1. **Job dates were lost.** A tab before the dates, or a dash without spaces, cut most of a
   resume's job dates apart. Dates are now located first, then the line is split.
2. **Job descriptions were flattened to one line**, so requirements were never found. HTML now
   keeps paragraph and list structure.
3. **The analyzer split postings by a fixed set of heading words.** It now classifies each
   posting's own headings and stops at legal and pay boilerplate. Of 62 live postings, 5 still
   yield no requirements.
4. **Reasoning models used up the output budget thinking.** Replies were cut off and read as
   malformed JSON, so every bullet was skipped, at 60 to 80 seconds a call.
   - OpenRouter calls now turn reasoning off, with a fallback for models that cannot.
   - Cut-off replies are retried once with more room.
   - `<think>` blocks are stripped, and JSON is found inside prose.
   - Result on the same resume and posting: tailoring 460s to 18s; 0 bullets changed to 3.
5. **The Word-to-PDF step failed on rebuild** (COM not initialized on that thread). The
   converter now initializes and releases COM around each conversion.
6. **The answer-bank screen crashed** on a form that asks the same question twice.
7. **A default fit score of 80** was still written when a posting had no scoreable content.
   It is now stored as unknown.
8. **A model provider that is overloaded** is now waited out longer and reported in plain
   words instead of a raw error.
9. **Maximum salary 0 blocked all jobs** with a minimum salary set. It now means no maximum.

## Open

- **Speed with free models:** a full tailor plus rebuild takes about 2 minutes, mostly waiting
  on the provider. A paid non-reasoning model would be faster and more reliable.
- **Explanation quality:** the "Evidence" line for an edit should show the real supporting fact
  (decision 021).
- **The length-correction pass** has not run against a real overflow (decision 022).
- **Sign-in and two-account isolation** have not been tested live (decision 023).
- **Lever coverage is thin:** 8 companies, 18 matches for "Product Marketing Manager".

## What this says about testing

Every one of these passed the existing tests. The tests use hand-written postings and stubbed
models; real postings and real models differ in structure, speed and behavior. Real-data runs
belong in the routine: rerun this one whenever the parser, analyzer, model client or pipeline
changes.
