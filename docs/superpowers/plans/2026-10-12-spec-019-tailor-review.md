# Tailor Review Clarity, Batch Decisions, and AI-Assisted Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every proposal readable and distinct, let a person decide on selected proposals together, and offer conservative AI-assisted decisions chosen before tailoring.

**Architecture:** Keep `ResumeChange` and the existing regeneration/validation pipeline authoritative. Add pure shared review-label, duplicate-identity, decision, and automatic-policy helpers in `product/`; expose batch mutation and mode through the workspace API; render the same saved state in Next.js and Streamlit. Serialize review read/check/write under the existing per-user cross-process batch lock and use a separate review revision, not the artifact version, for stale requests.

**Tech Stack:** Python 3.14, pytest, FastAPI/Pydantic, Streamlit, Next.js 16/React 19/TypeScript, Playwright.

**Spec:** `specs/019-tailor-review-clarity-batch-and-ai-assisted-decisions.md`

## Global Constraints

- Preserve decision 018's global free-form bullet matcher and existing change IDs; no speculative diff rewrite.
- No new model call, dependency, account, deployment, job submission, or push.
- A failed artifact remains unavailable for download/Apply after any decision; always rebuild through the existing pipeline.
- Do not use real resumes or `D:/Yang/Vibe Coding/job-copilot-local-data`, `~/.job_copilot`, or the current `.codex-pytest-live-data` in tests. Use synthetic fixtures and a new scratch directory.
- Preserve `.claude/settings.local.json`. Work only on `codex/truthful-tailoring-sources-publication` unless the user directs otherwise.
- Test both frontends because they share saved review state; keep format-2 reviews loadable.

## Review Focus

1. Two distinct bullets sharing one requirement: tests in Tasks 1 and 5 must show distinct full before/after text, with no accidental deduplication.
2. Identical wording in two source positions: Task 1's test must keep two separately decidable IDs.
3. A second tab changes a decision before a batch request: Tasks 2 and 4 must reject the stale revision without any partial write.
4. A failed or uncertain proposal is selected or auto-reviewed: Tasks 2, 3, and 4 must keep it out of auto-accept and preserve final validation gates.
5. A legacy saved review lacks mode/origin/revision: Tasks 2, 4, and 6 must load it as manual, initialize a revision safely, and retain its existing decisions.

---

### Task 1: Diagnose duplicates and make review labels honest

**Files:**
- Modify: `product/resume_tailorer/ui/tailor_progress.py`
- Test: `product/tests/test_tailor_progress.py`
- Inspect only: `product/resume_tailorer/diff_generator.py`, `product/resume_tailorer/artifacts/changes.py`

**Interfaces:**
- Consumes: `ResumeChange` and its `section`, `source_index`, `original_text`, `proposed_text`, `category`, `job_requirement`.
- Produces: `change_title(change: ResumeChange, ordinal: int) -> str` and `duplicate_key(change: ResumeChange) -> tuple | None`; the latter returns `None` without an anchored source identity. A free-form diff ordinal is not a source anchor. Neither helper drops a change.

- [ ] **Step 1: Write failing synthetic tests.** Add tests where two `ResumeChange` objects have the same job requirement but different original/proposed text; assert different `change_title` values. Add two objects with identical text but different `source_index`; assert different `duplicate_key` values. Add one unanchored free-form change; assert `duplicate_key` is `None`.

```python
assert change_title(change("a", original="Built sales reports", proposed="Built SQL reports"), 1) != change_title(change("b", original="Led customer surveys", proposed="Led survey analysis"), 2)
assert duplicate_key(replace(change("a"), source_index=1)) != duplicate_key(replace(change("b"), source_index=2))
assert duplicate_key(replace(change("freeform:0"), source_index=0)) is None
```

- [ ] **Step 2: Run the focused test red.** From `product/`, run `.\.venv\Scripts\python.exe -m pytest tests/test_tailor_progress.py -q`; expect missing helpers.
- [ ] **Step 3: Implement only the title/key helpers.** Build a bounded display excerpt from both before and after, include section and ordinal, and do not substitute the requirement for the proposed text. A duplicate key includes section, anchored index/span, original, and proposed; no anchor means no automatic duplicate identity.

```python
def duplicate_key(change: ResumeChange) -> tuple | None:
    anchor = change.baseline_span if change.baseline_span is not None else (
        change.source_index if not change.change_id.startswith("freeform:") else None
    )
    return None if anchor is None else (change.section, anchor, change.original_text, change.proposed_text)
```

- [ ] **Step 4: Run the test green; inspect a synthetic multi-change fixture to establish whether actual duplicate keys occur.** Record the result in the Task 7 experiment. Do not alter `_compute_changes` from the screenshot alone.
- [ ] **Step 5: Commit only this deliverable.** `git add product/resume_tailorer/ui/tailor_progress.py product/tests/test_tailor_progress.py`; `git commit -m "fix: distinguish tailoring review items"`.

### Task 2: Shared, versioned decision transaction

**Files:**
- Create: `product/resume_tailorer/review_decisions.py`
- Modify: `product/resume_tailorer/review_store.py`, `product/resume_tailorer/ui/tailoring_view.py`
- Test: `product/tests/test_review_persistence.py`, `product/tests/test_tailoring_view.py`

**Interfaces:**
- Consumes: a saved state dict, `group_changes(visible_changes(...), true_gaps)`, `save_review/load_review`, and the per-user OS lock in `batch_runner._file_lock(user_dir)`.
- Produces: `apply_decisions(state: dict, entries: list[tuple[str, str]], *, origin: str, expected_revision: int) -> dict` returning a new state, `ReviewConflict`/`ReviewSelectionError`, and `mutate_saved_review(folder: str, job_id: str, expected_revision: int, entries: list[tuple[str, str]], origin: str) -> dict`. Existing single-item endpoints will call the same mutation path. Revision starts at 0 for legacy reviews and increases once per successful changed transaction; artifact `version` remains separate.

- [ ] **Step 1: Write failing tests** for two valid selections applied together; an unknown, duplicate, blocked, or hidden ID causing no change; a wrong revision causing `ReviewConflict`; an unchanged retry being idempotent; a format-2 review with no new keys retaining decisions. Test `save_review=False` leaves the previous file intact.

```python
before = {**synthetic_state, "review_revision": 0}
after = apply_decisions(before, [("a", "ACCEPTED"), ("b", "REJECTED")], origin="person", expected_revision=0)
assert after["decided"] >= {"a", "b"} and after["review_revision"] == 1
assert before["decided"] == set()
with pytest.raises(ReviewConflict):
    apply_decisions(after, [("a", "REJECTED")], origin="person", expected_revision=0)
```

- [ ] **Step 2: Run the focused tests red.** From `product/`, run `.\.venv\Scripts\python.exe -m pytest tests/test_review_persistence.py tests/test_tailoring_view.py -q`.
- [ ] **Step 3: Implement pure validation/copy-on-write mutation.** Validate all IDs against the current reviewable set before changing anything; reject unsafe acceptance of `ValidationStatus.FAIL` or blocked proposals in the batch path, but permit keeping originals. Store `decision_origins[id] = {"by": origin, "reason": reason}`. Include `review_revision`, `review_mode`, and `decision_origins` in `review_store.signature` so Streamlit persists them.

```python
revision = int(state.get("review_revision", 0))
if expected_revision != revision:
    raise ReviewConflict("This review changed in another tab. Reload it and choose again.")
selected = {change_id for change_id, _ in entries}
if len(selected) != len(entries) or not selected <= eligible_ids:
    raise ReviewSelectionError("Select only changes in this review.")
```

- [ ] **Step 4: Put saved mutation under one short cross-process lock.** Derive `user_dir = Path(folder).parent` only after validating that `folder` is that user's artifacts directory. Under `batch_runner._file_lock(user_dir)`, reload, check revision, call pure mutation, save once, and raise on failed save. Do not hold the lock during model calls or PDF conversion. If current publication paths also write this review, use the same lock order and add a concurrency regression.
- [ ] **Step 5: Run focused tests green and commit.** `git add product/resume_tailorer/review_decisions.py product/resume_tailorer/review_store.py product/resume_tailorer/ui/tailoring_view.py product/tests/test_review_persistence.py product/tests/test_tailoring_view.py`; `git commit -m "feat: save review decisions atomically"`.

### Task 3: Conservative AI-assisted policy

**Files:**
- Create: `product/resume_tailorer/ui/assisted_review.py`
- Test: `product/tests/test_assisted_review.py`
- Modify: `product/resume_tailorer/review_decisions.py`

**Interfaces:**
- Consumes: `ResumeChange`, `ValidationStatus`, `ChangeCategory`, source-anchor metadata, the shared reviewable/blocked grouping, and `apply_decisions` from Task 2.
- Produces: `recommend_decisions(changes: Iterable[ResumeChange], blocked_ids: set[str]) -> tuple[list[tuple[str, str]], dict[str, str]]`; only safe accept/reject entries for reviewable changes are returned, with a plain reason per ID. Existing `safe_default_dispositions` continues to reject blocked changes before this policy runs. `apply_assisted_review(state: dict) -> dict` applies recommendations once at initial review creation, with origin `AI-assisted`.

- [ ] **Step 1: Write failing policy tests** for passing anchored rephrases, failed proposals, ambiguous pairing, unknown status, unanchored additions, removals/condensing, repeated same-text source positions, project/tool scope failures, and a second call that does not overwrite a person's later decision.

```python
entries, reasons = recommend_decisions([safe_rephrase, failed_claim, condensed, unanchored], set())
assert (safe_rephrase.change_id, "ACCEPTED") in entries
assert (failed_claim.change_id, "REJECTED") in entries
assert condensed.change_id not in dict(entries)
assert unanchored.change_id not in dict(entries)
assert all(reasons.values())
```

- [ ] **Step 2: Run `tests/test_assisted_review.py` red.**
- [ ] **Step 3: Implement the narrow policy** using existing per-change status and source identity; `PASS` alone is insufficient. Do not call the LLM again. A failed but reviewable proposal can be auto-rejected; a blocked gap is handled by `safe_default_dispositions`; uncertainty remains undecided. Pass recommendations through Task 2's mutation function, then through the normal final rebuild/validation path in each frontend. Leave the current failing artifact blocked until it passes a rebuild.

```python
safe = (change.validation_status is ValidationStatus.PASS
        and change.category is ChangeCategory.REPHRASED
        and bool(change.original_text and change.proposed_text)
        and duplicate_key(change) is not None
        and change.change_id not in blocked_ids)
```

- [ ] **Step 4: Run tests green and commit.** `git add product/resume_tailorer/ui/assisted_review.py product/resume_tailorer/review_decisions.py product/tests/test_assisted_review.py`; `git commit -m "feat: add conservative assisted review policy"`.

### Task 4: Workspace API mode and batch endpoint

**Files:**
- Modify: `apps/api/app/workspace/tailor_router.py`
- Test: `apps/api/tests/test_workspace_tailor.py`, `apps/api/tests/test_tailor_review.py`, `apps/api/tests/test_workspace_claim_scope.py`

**Interfaces:**
- Consumes: Task 1 title/key, Task 2 mutation/revision, Task 3 policy.
- Produces: `POST /v2/tailor/decisions/batch` with `{expected_revision: number, decisions: [{change_id, decision}]}`; `GET /v2/tailor` review fields `review_revision`, `review_mode`, change `title`, `category`, `decision_origin`, `decision_reason`; `POST /v2/tailor/run` accepts `review_mode: "manual" | "assisted"`. Existing single-decision endpoint remains compatible and advances revision.

- [ ] **Step 1: Write failing API tests.** Run synthetic stub tailoring in each mode. Assert default manual has undecided changes; assisted accepts only safe changes and reports reason/origin. Post two decisions with the current revision and assert one increment; post stale/unknown/blocked/mixed IDs and assert 409/400 with unchanged GET state. Verify legacy single endpoint still works and fails to save neither partial success nor false 200.

```python
review = client.get("/v2/tailor").json()["review"]
response = client.post("/v2/tailor/decisions/batch", json={"expected_revision": review["review_revision"], "decisions": [{"change_id": c["id"], "decision": "REJECTED"} for c in review["changes"][:2]]})
assert response.status_code == 200
assert response.json()["review_revision"] == review["review_revision"] + 1
```

- [ ] **Step 2: Run the focused API tests red.** From `apps/api/`, set `PYTHONPATH` to the repo's `product` path and run `.\.venv\Scripts\python.exe -m pytest tests/test_workspace_tailor.py tests/test_tailor_review.py tests/test_workspace_claim_scope.py -q`.
- [ ] **Step 3: Extend request/view models and call shared helpers.** Store selected mode before background work starts, apply assisted policy only after run tailoring and safe-gap defaults, and regenerate/validate before publishing a completed review. Return 409 on revision conflict and 400 on invalid selection; do not expose internal paths or model keys in error bodies. Keep no-review and legacy responses compatible.
- [ ] **Step 4: Run focused API tests green; then run `apps/api/` suite.** Commit the endpoint and tests with `git commit -m "feat: expose batch and assisted tailoring review"`.

### Task 5: Next.js full-text and batch review UI

**Files:**
- Modify: `apps/web/src/app/tailor/page.tsx`, `apps/web/src/app/tailor/review.tsx`, `apps/web/src/lib/types.ts`
- Create: `apps/web/src/app/tailor/change-list.tsx` if `review.tsx` exceeds a focused size
- Test: `apps/web/e2e/journey.spec.ts`; add `apps/web/e2e/tailor-review.spec.ts` for focused stub cases

**Interfaces:**
- Consumes: Task 4's API fields and batch endpoint; existing `ChangeCard` can remain the focused detail view.
- Produces: pre-run radio mode, distinctive queue titles, full-text all-changes view, accessible selection, selected count, atomic accept/reject calls, and conflict reload behavior.

- [ ] **Step 1: Add failing browser tests** for manual default and assisted choice before run; two rows with one shared requirement but distinct before/after; long text visible without `truncate`; show-all; checkbox keyboard operation; select-all-visible and clear; batch accept/reject; reload retaining origin; 409 conflict reloading without false success; failed artifact still lacking download/Apply.

```ts
await expect(page.getByRole("radio", { name: /I'll review changes/ })).toBeChecked();
await page.getByRole("button", { name: "Show all changes" }).click();
await expect(page.getByText("Built weekly SQL dashboards used by regional teams", { exact: true })).toBeVisible();
await page.getByRole("checkbox", { name: /Select change 1/ }).check();
await expect(page.getByText("1 selected")).toBeVisible();
```

- [ ] **Step 2: Run focused Playwright test red with its synthetic stub server.** From `apps/web/`, run the local Node binary at `D:/Yang/Software/cursor/NodeJs/node.exe` with `node_modules/@playwright/test/cli.js test e2e/tailor-review.spec.ts`.
- [ ] **Step 3: Implement mode and review UI.** Use `RadioGroup` outside collapsed Settings. Use separate checkbox and focus button controls, semantic labels, and `whitespace-pre-wrap break-words` for full text. `Show all changes` renders every card or a full-detail list without truncation; do not send HTML from resume text. Send one batch request with `review_revision`, clear selected IDs only after success, and reload on conflict. Use explicit origin/check text, not color alone. Keep the existing per-item manual-edit actions.

```tsx
<RadioGroup legend="Who reviews proposed changes?" name="review-mode" value={reviewMode}
  options={[{ value: "manual", label: "I'll review changes" }, { value: "assisted", label: "AI-assisted review" }]}
  onChange={setReviewMode} />
```

- [ ] **Step 4: Run focused Playwright, lint, and types green.** From `apps/web/`, run `node.exe node_modules/eslint/bin/eslint.js src e2e` and `node.exe node_modules/typescript/bin/tsc --noEmit` using the explicit Node path. Commit `git commit -m "feat: review full tailoring changes in batches"`.

### Task 6: Streamlit parity and saved-review compatibility

**Files:**
- Modify: `product/resume_tailorer/pages/5_Tailor.py`
- Test: `product/tests/test_review_persistence.py`, `product/tests/test_streamlit_css_hooks.py`; add `product/tests/test_streamlit_tailor_review.py`

**Interfaces:**
- Consumes: Tasks 1–3's shared title, revisioned transaction, and assisted policy; existing `st.session_state[_STATE_KEY]` and `_save_review_if_changed`.
- Produces: pre-run mode selection, full-text all-changes expander, multiselect batch accept/reject, origin/reason display, and legacy review fallback.

- [ ] **Step 1: Add failing synthetic AppTest/pure tests** for mode before create, all-changes text, two same-requirement labels, selected-only batch mutation, old format-2 review load, and no auto-accept of failed/uncertain changes. Include the current `signature` persistence path so a saved mode/origin is not lost on rerun.

```python
legacy = load_review(str(tmp_path), "synthetic-job")
assert legacy.get("review_mode", "manual") == "manual"
assert legacy.get("review_revision", 0) == 0
```

- [ ] **Step 2: Run focused product tests red.**
- [ ] **Step 3: Implement parity without duplicating policy.** Use Streamlit radio before the create button, `st.multiselect` for exact visible IDs, two selected-action buttons, and an expander rendering original/proposed with safe `st.text`/escaped content. Call Task 2's transaction and Task 3's policy. Reload on conflict; do not overwrite newer disk state from session state. Existing one-at-a-time review remains available.
- [ ] **Step 4: Run focused tests green and commit.** `git commit -m "feat: mirror assisted batch review in Streamlit"`.

### Task 7: End-to-end verification and handoff

**Files:**
- Create: `discovery/experiments/2026-10-12-spec-019-tailor-review.md`, `decisions/042-tailor-review-modes-and-batch-safety.md`
- Modify: `AGENTS.md`, `HANDOFF-TO-CODEX.md`, `HANDOFF-TO-CLAUDE-CODE.md`, `specs/019-tailor-review-clarity-batch-and-ai-assisted-decisions.md`

**Interfaces:** No new runtime interface. Record observed evidence and remaining release risks.

- [ ] **Step 1: Run the product suite** from `product/` with `.\.venv\Scripts\python.exe -m pytest -q`; record exact pass/skip/fail and exit code.
- [ ] **Step 2: Run the API suite** from `apps/api/` with `PYTHONPATH` including `product/`, `.\.venv\Scripts\python.exe -m pytest -q`; record exact pass/fail/warnings and exit code.
- [ ] **Step 3: Run web lint, typecheck, and all Playwright cases** with explicit `D:/Yang/Software/cursor/NodeJs/node.exe`; record exact outcomes. Use a new synthetic `JOB_COPILOT_DATA_DIR`, never the user's live folder or `.codex-pytest-live-data`.
- [ ] **Step 4: Supervise a synthetic browser walkthrough**: select manual, inspect and batch-reject selected changes, rebuild; select assisted on a new synthetic job, inspect automatic origins and unresolved items, rebuild, and verify a failed artifact cannot be downloaded or handed to Apply. Do not submit any employer application.
- [ ] **Step 5: Record the diagnosis and decision.** In the experiment, distinguish repeated requirement labels from proven duplicate `ResumeChange`s and document whether any true duplicate was reproduced. In decision 042, record why deterministic conservative assisted review and atomic batch transactions were selected over an extra LLM judge or client-side loops. Update both handoffs and AGENTS with accurate status; mark spec shipped only if verification passes.
- [ ] **Step 6: Commit docs only after reviewing status.** `git add discovery/experiments/2026-10-12-spec-019-tailor-review.md decisions/042-tailor-review-modes-and-batch-safety.md AGENTS.md HANDOFF-TO-CODEX.md HANDOFF-TO-CLAUDE-CODE.md specs/019-tailor-review-clarity-batch-and-ai-assisted-decisions.md`; `git commit -m "docs: record tailoring review verification"`. Do not push.
