# Supervised run: spec 010 requirement review, end to end (2026-10-05)

**Why:** spec 010 requires at least one supervised end-to-end reproduction, because unit tests
alone don't show tailoring quality.

**Setup:**

- **Model:** the real pipeline (`tailoring_service.run_tailoring`) with the real model,
  `codex-cli` (the builder's ChatGPT plan through the Codex CLI, GPT-5.6-Luna with low reasoning
  effort).
- **Conversion:** Word to PDF through the installed Microsoft Word.
- **Data:** everything anonymized.
  - The posting is `product/tests/fixtures/ats/posting_marketing_analyst.txt`, built to contain
    all six acceptance cases.
  - The resume is a Word file (`List Bullet` style) built from
    `product/tests/fixtures/ats/__init__.py`.
  - The older role is left unconfirmed.
- **Observer:** Claude Code ran it; the builder reviews this record.

## Result of the final run (31 s, 1 model call)

**Validation:** PASS, 1 page before and after, no findings.

**The one proposed change**, mapped to "Proven project management experience leading cross-team
launches":

| Before | After |
|---|---|
| Led on-time delivery of a 6-month store launch across 4 teams, with weekly risk reviews | Led on-time **project** delivery of a 6-month store launch across 4 teams, with weekly risk reviews |

It passed every check (length, semantic drift, fabrication, unsupported terms). No other bullet
was changed.

**Requirement review:** "Required: 4 of 7 with evidence · Preferred: 0 of 2 · 1 required
credential or threshold not found".

| Section | Requirement | Status | Evidence | In this resume |
|---|---|---|---|---|
| Required | Active CPA license (hard requirement) | No evidence | none | n/a |
| Required | Bachelor's degree in Business, Economics… | Direct | "BS Economics, State University, 2019" | yes |
| Required | Advanced SQL for analysis… | Direct | Acme Retail bullet 1 | yes |
| Required | Experience with Snowflake | Mentioned only | Skills list | n/a |
| Required | Proven project management experience… | Transferable | Acme Retail bullet 2 | not named, so it became the target |
| Required | PM experience partnering with engineering… | Check yourself | Acme bullet 3 says "PM (project manager)"; the posting means product | n/a |
| Required | 4+ years of marketing analytics experience | Transferable, with "check your dates" | Acme Retail bullet 1 | yes |
| Preferred | Tableau dashboards… | No evidence | none | n/a |
| Preferred | Experience with Salesforce campaign data | Unconfirmed | Bluebird Goods bullet 1 (not confirmed) | n/a |

**Do-not-add list given to the model:**

- never add: CPA, PM, Tableau, Salesforce;
- list only: Snowflake.

**Pass conditions:**

- **No unsupported term appeared.** CPA, Tableau and "product manager" are absent from the
  tailored resume. Snowflake stays only in the skills line, and Salesforce only in the original
  Bluebird bullet.
- **Every supported requirement is shown or explained.**

**Readability check:** every applicable check passed on the PDF Word produced:

- text can be read;
- name and contact read back;
- every bullet reads back;
- text reads back whole and in order;
- roles read back in page order;
- no unknown symbols;
- standard headings.

## What the supervised run found (the reason it was required)

Four real problems that unit tests hadn't caught, each fixed with a test (commit `e59d32d`):

1. **Word "List Bullet" style bullets were read as plain text.**
   - The parser only accepted "List Paragraph" paragraphs with their own numbering. "List
     Bullet" and "List Number" carry the numbering in the style.
   - Result: no bullets were found at all, and "Acted as PM … for the 2024 loyalty program" was
     read as a new job because of the year.
   - The first run's review said "Required: 0 of 7 with evidence".
2. **"BS Economics" didn't count for a bachelor's requirement** when the parser left the degree
   inside the institution text. Degree levels now match their common abbreviations. Bare "MA"
   and "MS" never count, because they are also state abbreviations.
3. **"Shown in this resume" was too generous.** A transferable requirement counted as shown just
   because its evidence bullet existed, so the second run had nothing to work on and proposed no
   change. A requirement is now shown only when it is named, which is the improvement the
   research recommends (make genuine, implicit evidence explicit).
4. **Codex couldn't start, because Node.js wasn't on PATH** (a Cursor update moved it). It failed
   as "Codex returned no answer". It now says plainly that Node.js wasn't found.

## Not shown by this run

- **The model is cautious.** Over the runs it proposed zero or one change. That's acceptable:
  doing nothing is never a false claim. But it means the review, not the model, is doing most of
  the work here. A stronger or paid model, or a higher reasoning effort, may make more of the
  allowed improvements. That's the builder's cost decision.
- **The free-form path** (a PDF original) wasn't run end to end here. Its loop and guards are
  covered by stubbed-model tests (`test_optimizer.py`, `test_unsupported_claim_guards.py`).
- **No real person's resume was used** (by design: synthetic data only in this repo).
