# Job Copilot release-readiness execution plan

Spec: `specs/015-streamlit-real-model-batch-verification.md`.
Starting commit: `73c22fc` on main. Builder authorized steps 1–13 and routine decisions on 2026-10-10.
Ledger: `discovery/experiments/2026-10-10-release-readiness.md`.

## Global constraints

Use synthetic fixtures and explicit scratch folders only. Preserve `.claude/settings.local.json`, both frontends and legacy review compatibility. No employer submissions. No purchased services, fabricated credentials, invented participant feedback or unsupported completion claims.

## Tasks

1. Baseline: run the product/API suites, lint, types and 22 Playwright cases; record actual counts and failures.
2. Verification spec: write spec 015 before live testing (this plan follows it).
3. Streamlit batch: browser-run a live-model batch and verify navigation and progress.
4. Recovery: stop/continue/restart and profile freshness checks against scratch data.
5. Summary review: inspect and exercise the existing section-review implementation before deciding whether a fix is needed.
6. Web journey: synthetic resume through search, custom board, tailoring, review, downloads, Apply and Tracker.
7. Blockers: use a reproduction and regression test for each product fix, then verify affected and full suites as appropriate. Commit verified changes in small groups.
8. Frontend decision: designate Next.js primary; keep Streamlit available until migration and real-user validation justify retirement.
9. Model decision: evaluate the existing model's synthetic outputs. Make no paid-model purchase; document whether evidence justifies a later comparison.
10. Deployment preparation: inspect current configuration and create actionable setup, data durability, backup and recovery instructions.
11. Release: push verified commits under the current authorization and verify CI; deploy only when existing accounts/configuration permit it without a purchase or new legal agreement.
12. Accessibility/integrations: run available checks, package the helper, and prepare exact remaining Google/Gmail/store/screen-reader steps.
13. Usability: run three agent simulations, fix serious reproducible obstacles, and prepare the independent-participant protocol. Label simulations distinctly from user research.

## Review focus

Truthfulness and download/Prepare gates, cross-process batch ownership, stale-profile handling, URL/source provenance, credentials and data isolation, keyboard-accessible review controls, and honest verification/release reporting. Obtain one final independent code review if product code changes.
