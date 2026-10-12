# Spec 018: Only the current batch execution may publish its artifacts

**Status:** Approved and implemented locally on 2026-10-11. Reproduced overwrite, actual frontend hooks and two-process tests pass. Full suites/browser pass; live-model Continue and independent final sign-off remain open. See decision 040 and the specs-016–018 experiment.
**Plan:** `docs/superpowers/plans/2026-10-11-spec-018-batch-publication.md`.
**Date:** 2026-10-11
**Builds on:** specs 014–015, decision 037.
**Evidence:** `discovery/experiments/2026-10-11-evidence-upload-and-worker-probes.md`.

## Problem

Spec 015 fences batch status by execution ID, but `Hooks.tailor_one` writes artifacts/reviews
before the runner checks that ID again. A worker can lose ownership after an expired heartbeat,
then finish late and overwrite the resumed worker's review. The status remains `done` for the
current execution while its current review now contains the old result.

The deterministic probe blocked one synthetic worker, injected an expired heartbeat without
waiting three minutes, resumed the same job and saved `current`, then released the old worker.
The saved review changed from `current` to `old`; the batch execution ID stayed current.
It used the production runner and review store with deliberately minimal synthetic hook data,
not a real model or a full artifact pipeline. Inspection identifies the same unfenced writes
inside `batch.tailor_job`/`run_tailoring` in both API and Streamlit hooks.

## Goal

After recovery/Continue, an obsolete worker cannot replace the current review, resume files,
handoff or batch/run status. Keep long model work outside the batch lock; keep progress,
Stop-after-current, options, completed work and both frontends working as today.

## Recommended design: compute privately, publish under ownership

### 1. Execution-private staging

- Give each execution/job an isolated staging directory under the explicit user's test/data
  workspace, identified by batch ID, execution ID and safe job identifier. Do not derive paths
  directly from untrusted titles/URLs. Reuse safe hashed identifiers and validate containment.
- Both API and Streamlit hooks run the existing tailoring/regeneration pipeline into that
  staging directory with a private session. Intermediate PDFs, reviews and private handoffs
  must not write into the shared current-artifact directory while the model is still running.
- Split `batch.tailor_job`'s computation from publication with a small explicit result contract:
  computed review state plus staged artifacts. Existing single-job callers can retain their
  behavior; deployed batch hooks must use the fenced publication path. Merely passing a token
  while preserving unconditional shared writes does not meet this spec.

### 2. One checked publication boundary

- After computation, acquire the same cross-process batch-change lock used for recovery and
  claims. Under that lock, reread the batch and verify batch ID, execution ID, job ID and current
  running item. Compare token identity, not only PID or heartbeat age.
- Stop-after-current is not loss of ownership: a cancelled-but-draining execution may finish
  and publish its current job. Recovery/new execution invalidates the old token.
- If ownership is lost, discard the publication result: do not change shared review/artifact,
  active handoff, current item's outcome, on-finish/run-status or completed timestamps.
- If owned, publish staged immutable/content-addressed files, then atomically replace the
  review's current pointer/state and record the item outcome. Keep the ownership check and
  publication in one critical section: a check immediately followed by an unlocked write
  leaves the same race. A late callback cannot independently write shared run state.
- File publication must use atomic replacements where current readers are involved. Readers
  must never see a partially written review. Check `save_review`'s boolean result: failure
  cannot mark the batch item done or expose a new handoff.
- The lock covers short local publication, not model calls/conversion. Bound the publication
  work and its file sizes to existing limits. If it can exceed the lock's stale-owner timeout,
  explicitly strengthen lock ownership before relying on it; do not assume a long file copy
  is atomic or safe simply because a lock filename exists.

### 3. Failure and cleanup

- A failure before current review publication preserves the previous valid review and its
  handoff. Report the current execution's failure without publishing partial results.
- A restart may leave private staging files. Clean only validated staging paths belonging
  to finished/obsolete executions with a bounded retention rule; never delete a live worker's
  workspace or the master resume/current canonical artifact. Do not sweep the data root.
- A stale result cannot refund/reuse model requests retroactively. Keep existing limit
  accounting and the conservative three-minute/PID-reuse fallback; document remaining limits.
- This is a targeted ownership boundary in the shared batch flow, not a distributed queue or
  attempt to terminate arbitrary OS/model processes.

## Alternatives

- **Recommended:** staged results plus locked ownership-checked publication. Covers actual
  artifact writes while allowing non-blocking model work and recovery.
- **Rejected:** checking execution only after `tailor_one` returns. The reproduced review is
  already overwritten before the check.
- **Rejected:** checking before `save_review` without sharing the recovery lock; recovery can
  change ownership between the check and the write.
- **Deferred:** hold the batch lock across the entire model call or introduce a queue/database
  service. The former blocks Stop/Continue; the latter exceeds this scope/dependency agreement.

## Expected files and compatibility

`batch_runner.py`, `batch.py`, minimal artifact publication support, API `batch_router.py`,
Streamlit `ui/batch_panel.py`, product/API/AppTest/browser tests. Inspect `tailoring_service.py`,
`tailoring_session.py` and `review_store.py` to cover every write in the deployed hooks.

Keep public batch endpoints, enum values, saved options, existing batch IDs and review format 2.
New internal hook/result interfaces must be updated in both apps and all tests together.
Legacy saved batches receive a new execution token on Continue; they do not need invented old
ownership. No new dependency, paid service, real data, employer submission or broader refactor.

## Acceptance cases and definition of done

- [ ] Original blocked worker → expired heartbeat → resumed job → late original return:
      current review text, PDF bytes/hash, version, handoff and item outcome stay unchanged.
- [ ] Reproduce through both deployed batch hooks with deterministic model/converter responses,
      not only a custom runner hook. Cover actual saved reviews and published files.
- [ ] Current PDF download/Apply/helper still refer to the resumed artifact after the late return.
- [ ] Genuine two-process recovery/publication test covers the check/write race; thread-only
      tests do not establish cross-process isolation.
- [ ] Stop drains and publishes the owned current job; overlapping start/Continue/redo stay blocked.
- [ ] Failed publication and process interruption preserve prior valid files and allow recovery.
- [ ] Resume options/completed items, single-job redo and legacy reviews/batches still work.
- [ ] Staging cleanup never touches active execution/current artifacts or paths outside staging.
- [ ] Full suites and synthetic browser recovery exercise pass; evidence and limitations recorded.

**Review gate:** approve this written spec and the targeted hook/publication interface change
before the detailed implementation plan and code. No fix is claimed by this draft.
