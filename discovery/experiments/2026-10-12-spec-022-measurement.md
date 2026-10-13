# Spec 022 step 1: why tailoring changes so little (2026-10-12)

**Question:** is "0 changes" caused by the model's instructions or by the code checks that reject
rewrites?
**Setup:**
- **The app:** the local workspace API with the real model (`codex-cli`) and a fresh scratch data
  folder.
- **Resumes:** three synthetic ones: the e2e fixture (Word), a fuller analyst resume (Word, 7
  bullets), and the same fuller resume as a PDF.
- **Jobs:** real public postings from Greenhouse, Ashby and SmartRecruiters.
- **Excluded:** no personal data, and nothing was submitted.

## Results

**Run 1, facts not confirmed** (the state right after import):

| Resume | Runs | Changes shown | Turned down by checks | Final check |
|---|---|---|---|---|
| Fixture (Word) | 3 | 0, 0, 0 | 0 | Pass |
| Fuller (Word) | 3 | Could not run: "contact line missing or ambiguous" (bug 13) | — | — |
| Fuller (PDF) | 3 | 1, 1, 2 (cosmetic) | 0 | Warning, Warning, Fail |

After fixing bug 13, the fuller Word resume ran 3 times: 0 changes, 0 turned down, Pass.

**Why, proven on the model's input and output:**
- **The input:** for the fuller Word resume, the "make clearer" list in the model's input was
  **empty**. Every requirement was "Unconfirmed", because the facts hadn't been confirmed in
  Career Profile. Even "Extensive experience using SQL…" went onto the "do not add" list, though
  a bullet says "Built SQL and Tableau dashboards".
- **The output:** the model answered `"change": "keep"` for all 8 bullets.

**Run 2, facts confirmed** (a fresh scratch folder; the first had reached the app's limit of 15
runs a day):

| Resume | Runs | Changes shown | Turned down by checks | Final check |
|---|---|---|---|---|
| Fixture (Word) | 3 | 0, 0, 0 | 0 | Pass |
| Fuller (Word) | 3 | 0, 0, 0 | 0 | Pass |
| Fuller (PDF) | 3 | 4, 2, 5 | 0 | **Fail, Fail, Fail** |

- **Confirming facts fills the input:** the "make clearer" list had 4 targets, 2 of them
  required to be answered.
- **The Word path still changed nothing.**
- **The PDF path's changes were mostly synonyms**, such as "find" to "identify" and "cutting" to
  "reducing".
- **Every PDF failed its final check.** The model added "…using SQL, Python, Excel, and Tableau…"
  to the summary. The tool-scope check (decision 041) treats a new mention of a tool outside a
  list as a claim about one job, so it reported "can't verify that you used it in this project"
  for tools that appear word for word in the person's own bullets.

## Conclusions

1. **The checks are not what blocks tailoring.** They turned down 0 proposals in 15 completed
   runs. The model proposes little or nothing.
2. **Unconfirmed facts make tailoring do nothing, silently** (bug 15). Tailor never says so
   before a run.
3. **Even with confirmed facts and targets,** the Word instructions ("most bullets should end up
   unchanged…") produce no edits. That supports spec 022's level 1 instruction rewrite.
4. **The free-form path fails on a true summary sentence.** That is the decision 041 guard
   applied to a summary, which describes a whole career rather than one job. Changing it is a
   decision for the builder, because spec 022 keeps the guards unchanged.
5. **Evidence matching is sometimes weak:**
   - "stakeholder management" was paired with an Excel bullet instead of "Partnered with finance
     and merchandising leads…";
   - "5+ years of experience" was paired with a dashboards bullet.

   Noted for a later fix; it doesn't block spec 022.

Bugs 13 (date range read as a phone number) and 14 (doubled phone bracket) were found and fixed
during these runs; see `discovery/bug-hunt-2026-10-12.md`.
