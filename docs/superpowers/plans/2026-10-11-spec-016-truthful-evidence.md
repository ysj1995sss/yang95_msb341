# Claim-specific truthful evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task after builder review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block unsupported tool/project relationships and stop generic analytics evidence from establishing named-platform experience.

**Architecture:** Keep requirement-level qualification evidence separate from claim-local validation. Share a deterministic guard across Word, free-form, manual review and final validation; preserve the current diff matcher. Extend the existing term/status system without adding a semantic model or dependency.

**Tech Stack:** Existing Python, pytest, FastAPI, Streamlit, Next.js and Playwright environments.

**Spec:** `specs/016-scoped-truthful-tailoring-evidence.md` (approved 2026-10-11).
**Status:** Builder approved; implementation and full local verification completed. Independent final sign-off remains open after a spending-cap interruption. Reported review findings were reproduced/fixed; see decision 038 and the specs-016–018 experiment.

## Global Constraints

- "No new dependency or paid provider here."
- "Existing work-bullet matching, including decision 018's global greedy matcher, is not changed."
- "New saved fields have defaults and review format 2 still loads."
- "No real resume, submission, paid purchase or new account; no assertion that these tests are human research."
- "Decision/handoffs updated after implementation; push only on explicit authorization."
- Preserve both frontends and `.claude/settings.local.json`; never touch the unrelated home `.env`.

## Review Focus

- A failed experience proposal can currently be accepted and downgraded to a warning by `pdf/content_validator.py`; claim-local blockers must remain failures.
- A comma-heavy experience sentence is not a Skills section; list-like punctuation must not bypass attribution checks.
- Duplicate work text under different roles must not license introducing a tool from a guessed role.
- A named product in an `or` alternative or `such as` example is not automatically mandatory, nor evidence of every named tool.
- Whole-document refinement can move an existing tool into another bullet without adding a new whole-document term.

## Task 1: Name platform evidence explicitly

**Files:** modify `product/resume_tailorer/analyzers/ats_keywords.py`, `analyzers/requirement_review.py`; add `product/tests/test_scoped_requirement_evidence.py`.

**Interfaces:** consume existing `JobAnalyzer.analyze`, `build_review`, `RequirementRow.term_status` and `SUPPORTED`. Produce `explicit_platform_terms(text: str) -> tuple[str, ...]` plus additive requirement grouping metadata defaulting to conjunction behavior. Preserve existing enum values, `targets`, `shown_terms` and `blocked_terms` contracts.

- [ ] Step 1: write failing behavior tests with literals. Start with the observed Qualtrics failure, then cover conjunction, alternative, example, listed/unconfirmed/confirmed and unknown-brand cases.

```python
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import build_review
from tests.fixtures.ats import profile

def test_generic_analytics_does_not_establish_qualtrics():
    candidate = profile()
    candidate.work_experience[0].responsibilities[0] = "Built SQL dashboards and analytics reports."
    posting = "Required Qualifications:\n- Experience with analytics platforms such as Qualtrics."
    review = build_review(JobAnalyzer().analyze(posting), candidate, posting=posting)
    row = next(r for r in review.rows if "Qualtrics" in r.text)
    assert row.status != "direct"
    assert ("Qualtrics", "none") in row.term_status
    assert "Qualtrics" not in row.shown_terms
    assert not row.hard_gate
```

Named fixtures: `SQL and Qualtrics` with SQL only → partial; `Qualtrics or SurveyMonkey` with explicit SurveyMonkey use → supported alternative, no Qualtrics target; `experience with NebulaForms` with generic analytics only → check; Qualtrics listed only → mention; unconfirmed contextual use → unconfirmed; confirmed contextual use → direct. Also assert the prompt never requests adding an unevidenced named example.

- [ ] Step 2: run the new test file using product Python and synthetic `--basetemp`; expect the Qualtrics assertion to fail on current direct evidence, not on fixture/import errors.

```powershell
$env:PYTHONPATH=(Join-Path (Get-Location) 'product')
& product/.venv/Scripts/python.exe -m pytest product/tests/test_scoped_requirement_evidence.py -q -p no:cacheprovider --basetemp=product/.venv/tmp-codex/spec016/platform-red
```

- [ ] Step 3: add named platforms and conservative explicit-brand recognition. Group recognized terms as all/any/example/uncertain; unknown explicit brands remain check-yourself. Compute each named term's status from its own exact passage. Generic evidence cannot satisfy missing named terms.

```python
# Seed extraction in requirement_review.py; existing vocabulary handles known tools.
def explicit_platform_terms(text: str) -> tuple[str, ...]:
    """Names in explicit platform patterns, never frequent-word fallback keywords."""
    named = [label for label in ("Qualtrics", "SurveyMonkey") if mentions(label, text)]
    if re.search(r"\b(?:with|using|such as|platforms?)\b|\be\.g\.", text, re.I):
        named += re.findall(r"\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b", text)
    return tuple(dict.fromkeys(named))

# Existing row construction must distinguish all, any and example requirements.
# Supported alternatives expose only evidenced alternatives in shown_terms/targets.
# An example does not become a hard gate and its unproven name is never a target.
```

Recognize Qualtrics and SurveyMonkey explicitly. Restrict unknown-name detection to explicit platform/tool patterns and a conservative branded-name shape; uncertain grammar/name interpretation yields check rather than a guessed direct match. Retain matched posting text and quoted evidence.
For an explicit tool/platform pattern whose object cannot be classified by this seed or the
existing vocabulary, emit the uncertain/check branch; never silently fall back to generic
analytics. Table-driven tests include lower-case unknown product wording for this branch.

- [ ] Step 4: run the new file, existing `test_requirement_review.py`, `test_unsupported_claim_guards.py`, `test_keyword_report.py`, then the full product suite. Expected: all green; record actual counts and original warnings separately.
- [ ] Step 5: commit only this verified deliverable with `fix: distinguish named platform evidence from generic capability`.

## Task 2: Apply the claim-local guard to every artifact path

**Files:** create `product/resume_tailorer/analyzers/claim_scope.py`; modify `tailorer/docx_bullet_tailorer.py`, `tailorer/optimizer.py`, `artifacts/changes.py`, `artifacts/regeneration.py`, `tailoring_service.py`, `pdf/content_validator.py`; add `product/tests/test_claim_scope.py` and extend existing artifact/unsupported/manual tests.

**Interfaces:** produce `introduced_unscoped_tools(original: str, proposed: str, profile: CareerTruthProfile, *, section: str = 'work_experience', review: RequirementReview | None = None) -> list[str]`. Extend `validate_manual_text` with keyword-only `section` defaulting to work experience; update real section callers. Consume exact original passage and section, not a guessed matching profile role. Use existing source-index/span mappings for source association; new context fields, if necessary, default to unknown.

- [ ] Step 1: reproduce the cross-role failure at a public validator, not just the new helper.

```python
from resume_tailorer.artifacts.regeneration import validate_manual_text
from resume_tailorer.models import WorkExperience
from tests.fixtures.ats import profile

def test_tool_from_another_role_cannot_be_added_to_this_project():
    candidate = profile()
    candidate.skills.append("Tableau")
    candidate.work_experience.append(WorkExperience(
        "Example B", "Analyst", "2023-2025",
        ["Built Tableau dashboards for inventory planning."], [],
    ))
    original = candidate.work_experience[0].responsibilities[0]
    issues = validate_manual_text(original, original + " using Tableau", candidate)
    assert any("Tableau" in issue for issue in issues)
```

Add literal cases for the tool only in Skills, another project in the same role, duplicate source bullets, the tool absent from the posting, and a comma-heavy work sentence. Positive controls retain explicit original Tableau/SQL use, truthful spelling aliases and Skills reordering. Summary may retain listed terms as listed skills, but not newly attach them to an employer/project.

- [ ] Step 2: run the new guard/manual tests. Expected: the current manual validator admits the wrong-project claim and fails the assertion.
- [ ] Step 3: implement deterministic local relationships and wire all consumers.

```python
issues = introduced_unscoped_tools(
    change.original_text, effective_text, profile,
    section=change.section, review=review,
)
```

Build the protected tool set from curated tool/platform spellings, named tools in the review, and specific tools the person actually lists; do not treat every generic competency as a product. A newly introduced tool-use relationship needs explicit support in the source activity. No source context means no permission to borrow another passage. Preserve original mentions and true skill lists. Reject unsafe Word edits while retaining rejected text/reason. Mark unsafe free-form proposals as FAIL and require correction/rejection. At rebuild, validate the effective selected text for every disposition, not only manual edits. Reject a refinement that moves a tool into an unsupported activity even if that tool appeared elsewhere in the previous whole document.

- [ ] Step 4: add final-PDF acceptance tests. A manually selected/accepted cross-role tool claim must not become `USER_CONFIRMED_UNVERIFIED_CLAIM` WARNING. Recompute this specific hard blocker from source/effective text in `validate_pdf_content` and preserve existing behavior for unrelated legacy warning classes. Rejected/restored source text remains usable. Run both real artifact paths with only model/network/converter boundaries stubbed where unavoidable.

```python
# Final validation contract for a produced artifact containing this new relationship:
assert validation.status.value == "FAIL"
assert validation.has_code("UNSUPPORTED_TOOL_ATTRIBUTION")
# Rejecting the proposal and rebuilding must remove it and recover usable output.
```

- [ ] Step 5: run full product and API suites with synthetic data; commit with `fix: enforce project-local tool evidence through final review` only after green.

## Task 3: User-visible safeguards and release verification

**Files:** extend existing API Tailor tests, `product/tests/test_freeform_sections.py`, `product/tests/test_apply_freshness.py` as needed; add `apps/web/e2e/truthful-evidence.spec.ts`; update existing shared review labels only where required. Record a new experiment/decision and update AGENTS and both handoffs after implementation.

**Interfaces:** existing FAIL/rejected reason payloads and Apply/download readiness; retain all existing API fields and review format 2.

- [ ] Step 1: add an API/browser regression that offers a wrong-project Tableau edit, exercises Accept and rebuild, and verifies the gate; reject it and rebuild, then verify recovery. Use synthetic fixtures and labeled deterministic model responses.

```typescript
// Within the existing synthetic e2e server fixture:
await expect(page.getByText(/can't verify.*project/i)).toBeVisible();
await expect(page.getByRole("link", { name: /Download PDF/i })).toHaveCount(0);
```

Test source-specific error explanations in both apps, Skills versus Summary decisions, a legacy review with no new metadata, and unchanged truthful content. Keep work-bullet matching untouched.

- [ ] Step 2: run the new public tests and observe the expected failure before adding missing presentation wiring.
- [ ] Step 3: reuse the shared guard message in UI/API; do not introduce a new score or employer-screening claim.
- [ ] Step 4: run full product/API, ESLint, TypeScript, Playwright and a synthetic real-model browser exercise when available. Record generated versus seeded edits and exact outcomes; no independent human pass is implied.
- [ ] Step 5: obtain one fresh-context whole-branch review under executing-plans, fix important findings with RED→GREEN tests, record decisions and commit docs locally. No push/merge without authorization.

## Verification commands

Use each task's unique ignored scratch directory; create its parent explicitly on Windows. Product runs from the repository root with product on PYTHONPATH. API runs from `apps/api` using its Python and `site.addsitedir` for the existing product packages. Do not install dependencies to resolve local venv differences.

```powershell
& product/.venv/Scripts/python.exe -m pytest product/tests -q -p no:cacheprovider --basetemp=product/.venv/tmp-codex/spec016/full
# From apps/api, with product PYTHONPATH:
& .venv/Scripts/python.exe -c "import site; site.addsitedir('D:/Yang/Vibe Coding/yang95_msb341/product/.venv/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(['tests','-q','-m','not live','-p','no:cacheprovider','--basetemp=.venv/tmp-codex/spec016/full']))"
# From apps/web:
& 'D:/Yang/Software/cursor/NodeJs/node.exe' node_modules/eslint/bin/eslint.js src e2e
& 'D:/Yang/Software/cursor/NodeJs/node.exe' node_modules/typescript/bin/tsc --noEmit
& 'D:/Yang/Software/cursor/NodeJs/node.exe' node_modules/@playwright/test/cli.js test
```

For browser tests set existing API-venv `PYTHON`, product-package `PYTHONPATH`, Node PATH and an explicit ignored synthetic `E2E_DATA_DIR`, as in the preceding experiment. Expected after implementation: exit 0 for every command; report observed counts, not predicted totals.

## Self-review and handoff

All spec-016 sections map to Tasks 1–3. The five review-focus cases have tests in their owning tasks. Task 2 consumes Task 1's term/status representation; Task 3 consumes the unchanged FAIL/reason/readiness contract. The named-platform parser must not weaken claim-local guards, and legacy context must not grant new relationships.

Recommended execution: native in this session, with one independent whole-branch review at the end. Builder review of this plan is required before product edits.
