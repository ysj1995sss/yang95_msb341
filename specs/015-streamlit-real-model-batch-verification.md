# Spec 015: Verify the release workflows with synthetic data

Status: Authorized for execution by the builder's request to complete steps 1–13 without intermediate questions (2026-10-10). Results belong in `discovery/experiments/2026-10-10-release-readiness.md`.
Local verification and authorized release completed 2026-10-11: `bbe372f`, all five CI
jobs passed. Deployment, real account integrations, manual screen readers and independent
participants remain pending as documented; agent simulations are not human research.

## Goal

Prove that the existing batch and application-preparation workflows work through their browser interfaces, find and repair reproducible blockers, and prepare a release that can be tested by other people. Builds on specs 009 and 012–014; it does not introduce a new application-submission capability.

## Data and runtime

- Use only new scratch directories inside the repository's ignored test workspace. Never read or run experiments against the builder's real data folders.
- Import `apps/web/e2e/fixtures/resume.docx`. Additional fixtures must be synthetic.
- The live model is the existing local `codex-cli` configuration. Record availability, latency and validation results; a stub is never evidence of live-model success.
- Use distinct ports and explicit data directories for each test server. Stop only processes launched for this experiment.
- Keep credentials out of logs and git. Use the repo's model configuration; leave the unrelated home-directory `.env` alone.

## Acceptance checks

1. Record fresh product, API, lint, type-check and Playwright results, including skipped tests and process exit status.
2. Start a 2–3-job batch in the Streamlit browser. Verify that progress updates, another page remains usable, and returning to Jobs preserves the batch.
3. Stop after the current job and continue only unfinished jobs. Restart the experiment's server mid-job and verify recovery without redoing completed jobs.
4. Edit the synthetic Career Profile. Verify stale warnings and blocked Prepare, then tailor one job again and verify the other batch items remain visible.
5. Reproduce free-form summary review using section-level accept/reject/manual edits and rebuilding. Resolve the conflict between the older limitation statement and spec 012 with observed evidence.
6. Exercise the Next.js journey: import, confirm, search, add a board, save, tailor, review, download, prepare and Tracker. A test status change is confined to scratch data; no employer submission occurs.
7. Repair demonstrated journey blockers with focused regression tests. Keep existing compatibility, profile provenance and truthfulness gates.
8. Run keyboard, mobile and automated accessibility checks. Report assistive-technology evidence precisely: accessibility-tree inspection does not establish a human screen-reader pass.
9. Record the primary-frontend and model choices, release prerequisites, account-dependent checklists, and reproducible test instructions.
10. Run three clearly labeled agent usability simulations and prepare the protocol for 2–3 independent participants. Record zero human participants unless actual people participate; never fabricate quotes or approvals.

## Release boundary

The current request authorizes completing the previously proposed release steps, including committing and pushing verified changes. Public deployment can proceed only with an already usable configuration and credentials, without inventing secrets or enrolling in a paid service. If hosting, Google consent, Gmail access, store registration or human participation is unavailable, finish the local preparation and document the exact outstanding action.

## Completion evidence

The experiment record must separate passed, failed, blocked and untested checks; identify commits and commands; and retain any material limitations. Update AGENTS.md and both handoffs after verified work. Existing test counts are a comparison baseline, not a substitute for fresh execution.
