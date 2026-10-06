# Supervised runs: spec 011 (2026-10-05)

**Why:** spec 011 requires two real runs, not just unit tests:

1. **Word resume:** a Career Profile edit must reach the tailored file.
2. **PDF resume:** the free-form path had never run with a real model.

**Setup (both runs):**

- **Model:** the real pipeline with the real model, `codex-cli` (the builder's ChatGPT plan,
  GPT-5.6-Luna, now with medium reasoning effort).
- **Data:** anonymized fixtures. The posting is `product/tests/fixtures/ats/posting_marketing_analyst.txt`
  (all six spec 010 cases). The Career Profile is `tests/fixtures/ats` plus one bullet added only in
  the profile: "Built Tableau dashboards for the loyalty program's weekly executive review".
- **Observer:** Claude Code ran them; the builder reviews this record.

## Run 1: Word resume, tailored from the Career Profile

**Conversion:** Word to PDF through the installed Microsoft Word.

**Final run:** PASS, 66 s, 4 model calls, no findings.

| Check | Result |
|---|---|
| The profile edit reached the Word file | Yes. "Brought your Career Profile into your Word file: 0 bullet(s) updated, 1 added, 0 removed." The new bullet uses the role's List Bullet style. |
| The dead end is closed | Tableau changed from "no evidence" (spec 010 run) to **direct evidence**, from the new bullet. |
| Model changes | 1: "Led on-time delivery…" became "Led on-time **project** delivery…" (passed every check). |
| Not changed, and why | "4+ years marketing analytics experience": "The existing bullet shows marketing analytics work, but cannot safely add a 4+ year duration without changing the verified evidence." |
| Keyword report | Added: none. Already named: SQL, Snowflake, Analytics, Tableau, Dashboards, Salesforce. Left out: "evidence, not named yet" (Product launch, Project management) and "no evidence" (CPA). |
| Unsupported terms | None (no CPA, no "product manager", Snowflake only in the skills line). |
| Readability | All 10 checks passed, including the second reader agreeing and the Word file checks (contact in the body; no tables or text boxes). |

## Run 2: PDF resume through the free-form path

**Final run:** WARNING (only "no original PDF to compare visually", which is expected for a
generated original), 28 s, 2 model calls.

| Check | Result |
|---|---|
| The profile edit reached the resume | Yes. The Tableau bullet is in the tailored text. |
| Unsupported terms | None (no CPA, no "4+ years", no "product manager"). |
| True facts kept | Yes. Salesforce stays in the Bluebird bullet. |
| Readability | All 8 free-form checks passed, including **every bullet reads back** (new for this path) and the second reader. |
| Keyword report | Added: Project management (in the summary, backed by transferable evidence). Left out: Product launch ("evidence, not named yet") and CPA ("no evidence"). |

## What the runs found and fixed (commit `69c3f67`)

1. **Degree requirements were targets the model can't act on.** The "shown" check looked only at
   bullets, so the bachelor's degree counted as not shown, and the model rightly said it can't
   add education through a bullet edit. A requirement backed only by education or a certification
   now counts as shown.
2. **A target got neither a rewrite nor a reason.** The rule was only in the user prompt; adding it
   to the output-format rules made the model answer.
3. **The free-form model deleted a true fact.** The first free-form run removed "Salesforce" from a
   real bullet to obey "must not appear anywhere they don't already". The wording now says to
   keep a term where it already is and never add it anywhere new.
4. **The guards caught a fabrication.** That first free-form run also wrote a summary claiming "4+
   years of experience", copied from the posting. The existing unsupported-claim check failed the
   resume until the change is rejected. The guard worked.

## Known limits (not fixed in spec 011)

- **Free-form summary changes aren't reviewable.** The free-form change list pairs bullets, not the
  summary paragraph, so a summary edit (here, adding "project management") can't be accepted or
  rejected on its own. It's covered by the unsupported-claim check, not by a review row.
- **Odd skills-line pairing.** The free-form change list sometimes pairs skills lines oddly (for
  example "SQL → (empty)" when skills move to another line). This is older behavior.
- **Model variance.** Across runs the model proposed 0–1 changes. It's careful rather than
  thorough; the review and the reasons make that visible.
