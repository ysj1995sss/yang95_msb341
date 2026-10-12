# Execution-owned batch artifact publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task after builder review. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure an obsolete batch worker cannot overwrite a resumed worker's review/artifact or current run status.

**Architecture:** Compute into private execution/job staging and return a staged result. The runner publishes under the same short cross-process lock as recovery, checking execution and running item ownership. API progress callbacks obey the existing API-lock-before-batch-lock order; long model/conversion work remains unlocked.

**Tech Stack:** Existing Python threads/files/atomic replace, pytest, FastAPI, Streamlit and browser tests; no queue service or new dependency.
**Spec:** `specs/018-batch-artifact-publication-ownership.md` (approved 2026-10-11).
**Status:** Builder approved; implementation, full suites, independent code review and real-model recovery checks completed. Both batches reached 2/2 after retries; two actual Word cleanup failures remain an unresolved release risk. See decisions 040/041 and the independent-review/live-Streamlit experiment.

## Global Constraints

- "Keep public batch endpoints, enum values, saved options, existing batch IDs and review format 2."
- "Compare token identity, not only PID or heartbeat age."
- "The lock covers short local publication, not model calls/conversion."
- "Check save_review's boolean result: failure cannot mark the batch item done or expose a new handoff."
- "Never delete a live worker's workspace or the master resume/current canonical artifact. Do not sweep the data root."
- "No new dependency, paid service, real data, employer submission or broader refactor."
- Preserve both frontends, canonical fact snapshots from spec 017 and local Claude settings; no push/merge without authorization.

## Review Focus

- API `_begin` holds `_RUNS_LOCK` before calling the batch runner: acquiring `_RUNS_LOCK` while already holding the batch file lock would deadlock.
- A cancelled-but-draining job is still owned and must publish; token loss on recovery is different from Stop.
- A returned False from save_review is failure, even when artifact bytes were staged successfully.
- A publisher interrupted after writing immutable bytes but before current review replacement must leave the old current review usable.
- Staging cleanup must reject symlinks/path escapes and avoid any still-live execution, including a superseded model hook still finishing.

## Task 1: Stage results and publish only under runner ownership

**Files:** create `product/resume_tailorer/batch_artifacts.py`; modify `batch.py`, `batch_runner.py`; add `product/tests/test_batch_artifacts.py` and extend `test_batch_runner.py`.

**Interfaces:** `StagedReview(state: dict, staging_dir: Path, artifacts_dir: Path)`; `stage_tailor_job(job, *, artifacts_dir, original_bytes, filename, llm, career_profile=None, provenance=None, target_length='preserve', conservative=False, fit_scorer=None) -> StagedReview`; `publish_staged_review(job_id: str, result: StagedReview) -> None`. Extend Hooks with `publish_result: Callable[[str, object], None]` default no-op; `tailor_one` may return a staged result. A current publication receives the result; deployed batch hooks must never save canonical files during computation. Existing direct `tailor_job` wrapper can retain immediate publication for non-batch callers.

- [ ] Step 1: add a production-storage runner test reproducing old-worker overwrite. Use Events and an injected expired heartbeat, not a three-minute sleep. The current public contract must first reproduce the failure before new hooks/interfaces are implemented.

```python
# In a tmp_path-only runner fixture, block the first worker and resume the same job.
# Use production save_review/load_review with changes=[] and distinct synthetic PDF bytes.
assert load_review(folder, "job-a")["marker"] == "current"
release_old.set()
assert old_finished.wait(5)
assert load_review(folder, "job-a")["marker"] == "current"  # currently becomes old
```

Add owned Stop/drain positive control, immutable artifact hash preservation, failure on False publication, and previous-review survival on interrupted publication. Ensure fixture helper always releases/joins its own threads in finally; no test leaves a writer running into another test.
The adverse hook calls the production `batch.tailor_job`/staged result path, with only model
and converter responses controlled. Do not use a permanently unfenced custom save_review
hook as an acceptance test: harmless legacy callbacks returning None remain compatible, but
arbitrary writes inside external callbacks are outside the deployed publication contract.

- [ ] Step 2: run the overwrite test and observe current → old failure with current batch token unchanged. Record the RED before changing production code.
- [ ] Step 3: split computation and publication. Use a validated private staging directory under `artifacts/.batch-staging/<execution>/<hashed-job>/<unique-attempt>`, passed by the runner/hooks; raw title/URL never enters a path. Run run_tailoring and optional safe-default regeneration with private session/artifact paths. Preserve all frozen review state, including source_info. Return bytes/state without writing a shared review.

```python
@dataclass
class StagedReview:
    state: dict
    staging_dir: Path
    artifacts_dir: Path

result = hooks.tailor_one(job_id)  # model/conversion writes private staging only
with _file_lock(user_dir):
    data = _read_batch_locked(user_dir)
    if owns_running_item(data, batch_id, execution, job_id):
        hooks.publish_result(job_id, result)
        # Write done only after publication succeeds; failure remains resumable.
```

Define `owns_running_item(data, batch_id, execution, job_id) -> bool` checking matching IDs/token and running item, with running or cancelled/draining batch state. No ownership → no canonical write and no item/on-finish updates. Canonical publication writes a validated content-addressed PDF atomically, then atomically replaces the review state. A private temporary handoff is not a global active handoff; saved-review opening publishes the current handoff as today. Check save_review's success, raise a user-visible failure on False, and retain the previous review. No staged paths leak into the saved canonical review.

- [ ] Step 4: run focused artifact/runner tests and full product suite. Existing harmless custom test hooks returning None can retain default no-op publication; neither deployed frontend may use that legacy mutation path.
- [ ] Step 5: commit with `fix: publish staged batch artifacts only for the current execution` after green.

## Task 2: Both real frontend hooks and safe API status callbacks

**Files:** API `apps/api/app/workspace/batch_router.py`, Streamlit `product/resume_tailorer/ui/batch_panel.py`, runner callback support; add `apps/api/tests/test_workspace_batch_publication.py`, `product/tests/test_streamlit_batch_publication.py`.

**Interfaces:** both hooks call `stage_tailor_job` and `publish_staged_review`. Add `ExecutionClaim(user_dir: Path, batch_id: str, execution: str, job_id: str | None)` and `when_current(claim: ExecutionClaim, action: Callable[[], None]) -> bool`, checking token under the batch file lock. Provide execution-aware status callbacks separately from harmless existing unit-test callbacks; deployed API callbacks use the execution-aware forms.

- [ ] Step 1: reproduce late publication through actual API and Streamlit hook factories. Stub only the writing/converter boundary with controlled late-return responses; keep staging, review storage and runner real. Assert current PDF bytes/hash/version and review state remain current, then open/download through the API and check actual response bytes.

```python
assert client.post("/v2/batch/open", json={"job_id": job_id}).status_code == 200
assert client.get("/v2/apply/resume").content == current_pdf_bytes
assert load_review(artifacts_folder, job_id)["pdf_bytes"] == current_pdf_bytes
```

Add a concurrent `_begin`/progress test that finishes within an Event-driven timeout, plus an old callback delayed until after Continue. Tests must catch deadlock and wrong run status, not only callback invocation counts.

- [ ] Step 2: run frontend-hook/race tests and observe the missing staging/fence or outdated write failure before implementation.
- [ ] Step 3: wire both hooks to staging/publication. Do not create Workspace/session state in the publication callback that writes unrelated Career Profile state. API progress/finish callbacks receive ExecutionClaim, acquire `_RUNS_LOCK` first, then call when_current; the canonical artifact publisher acquires no API lock. Never invoke an API-lock-taking callback from inside the batch lock.

```python
def update_api_status(claim, payload):
    with _RUNS_LOCK:
        when_current(claim, lambda: _write_run(owner_id, payload))
```

Runner dispatches execution-aware callbacks after releasing its own locks; the callback's guarded write remains atomic against recovery. Preserve single-run/batch exclusion, saved model options, limits and Continue/redo. If startup/finish timing exposes a status race, pin it with a failing public API test and derive the shown status from the current batch rather than trust an obsolete callback.

- [ ] Step 4: run full product/API suites and existing batch browser journey; commit with `fix: fence API and Streamlit batch publication and status` after green.

## Task 3: Two-process race, interrupted publication and safe retention

**Files:** `product/tests/test_batch_publication_processes.py` (new), publication cleanup code/tests, existing API/Streamlit/browser cases, experiment/decision and handoff docs.

**Interfaces:** staged directories are owned by unique attempts and carry current execution identity; `cleanup_staging(artifacts_dir: Path, *, now: float, retention_seconds: float) -> None` considers only old validated staging directories with no live worker. It never deletes current/canonical files. No browser test is a substitute for the two-process check.

- [ ] Step 1: add a Windows-spawn-safe two-process fixture. Process A stages then signals ready and waits; parent expires its heartbeat, process B resumes/publishes, then releases A. Use controlled file/Event barriers and bounded joins, not timing guesses. Verify the real shared review and PDF bytes after both processes exit.

```python
assert current_state["pdf_bytes"] == b"current synthetic artifact"
assert current_state["version"] == 2
assert batch["execution"] == resumed_execution
assert batch["items"][0]["status"] == "done"
assert process_a.exitcode == process_b.exitcode == 0
```

Add interrupted publisher, save_review False and hostile/symlink staging-path cases. Prove current and active stages are retained, stale completed stages alone are removed, and no path outside the staging root is affected.

- [ ] Step 2: run these tests; observe missing containment/retention behavior before adding it. Existing ownership positives may already pass from Tasks 1–2; record them as verification, not a newly claimed RED.
- [ ] Step 3: publish with bounded local atomic operations. Keep publication below the file lock's stale timeout or strengthen its ownership/renewal with a failing race test before relying on longer critical sections. Retain active private stages; cleanup only old inactive stages after path containment and symlink checks. Local publication failure leaves prior current review and handoff intact; orphan immutable bytes do not become current.
- [ ] Step 4: run full product/API/lint/types/Playwright and a synthetic real-model batch Stop/Continue/restart exercise when available. Re-run the exact late-worker reproduction and public current-download check. Report all counts and exceptions honestly.
- [ ] Step 5: independent whole-branch review under executing-plans; important findings get one RED→GREEN fix pass. Record the decision and update AGENTS/both handoffs; commit locally. Do not push or merge without builder authorization.

## Verification and self-review

Use existing runtime commands from the spec-016 plan with unique ignored `spec018` product/API/browser data. Two-process targets use importable test helpers and `multiprocessing.get_context('spawn')` on Windows; child processes receive explicit scratch paths and never default to personal data. Close only owned test servers/processes.

Spec-018 staging/ownership/failure/cleanup clauses map to Tasks 1–3. Each Review Focus case is assigned: lock order and draining → Tasks 1–2; False/interruption → Tasks 1 and 3; hostile/live staging → Task 3. Task 2 consumes Task 1's result/publisher; Task 3 tests that exact deployed contract. This plan runs after spec-017 so publication preserves accurate frozen fact/source metadata.

Recommended execution: native in this session with one fresh reviewer. Builder review of this plan precedes product edits and the targeted internal hook change.
