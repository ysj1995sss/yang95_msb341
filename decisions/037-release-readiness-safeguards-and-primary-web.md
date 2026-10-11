# 037 — Release safeguards and primary frontend

Date: 2026-10-11. Scope: spec 015; builder authorized steps 1–13 without intermediate questions.

## Evidence

See `discovery/experiments/2026-10-10-release-readiness.md` for real-model browser runs,
regressions, independent review, synthetic section exercise and exact verification.
See `2026-10-11-agent-usability-walkthroughs.md` for three labeled agent walkthroughs.
Actual independent human participants: **0**.

## Decisions

1. **Next.js is the primary product frontend.** Keep Streamlit maintained as a local fallback
   and diagnostic UI. Both share the same engine/data, and the existing Streamlit demo is
   not a multi-user deployment. Reject immediate Streamlit deletion: no independent user
   evidence or deployed-web migration supports retirement yet.
2. **Keep the existing local codex-cli model for supervised testing.** Do not buy or select
   a paid model without a provider budget and comparable evidence. A public signed-in
   deployment needs a supported remote provider; the local CLI remains local only.
   Validation and keyword evidence cannot prove all project/tool relationships.
3. **A stopped batch owns its current job until it finishes.** Keep heartbeats/refresh active
   while draining, block overlapping work, fence resumed executions and recheck stale
   recovery under the cross-process lock. Keep completed reviews and options on Continue.
   Reject merely hiding Continue: direct API callers must also be protected.
4. **Freshness belongs to the actual Apply file.** Check both the saved review's profile
   version and the handed-off PDF hash. Withhold stale/older/missing current PDFs from
   tracking, downloads and helper attachments; keep employer links available. Preserve
   absent-key legacy compatibility and existing manual tracking policy.
5. **Manual section edits preserve heading boundaries.** The live PDF exercise proved that
   trimmed Skills text absorbed EDUCATION. Preserve the newline at reviewed section spans
   and insertions; leave decision 018's global bullet matching intact.
6. **Windows profile saves tolerate brief read contention.** Retry atomic replacement for a
   bounded 20 attempts (10 ms between); preserve the previous file and propagate persistent
   failure. Clean up the temporary file; do not report a failed save as successful.
7. **Release evidence must distinguish preparation from external completion.** Account
   setup, deployment, real Google/Gmail, Store publishing, manual screen readers and
   independent user research remain pending until actually performed. Do not fabricate
   human approvals, participants, consent or deployment URLs.

## Consequences / follow-up

- Retain conservative all-review invalidation and three-minute heartbeat/PID-reuse fallback.
  Execution fencing does not cancel an obsolete model hook's artifact writes after a false
  heartbeat recovery. Any further ownership redesign needs its own spec.
- Summary/skills review already exists under spec 012/decision 034; decision 033's older
  limitation is superseded. Heading ambiguity and totally unsectioned text remain limited.
- Prioritize evidence specificity (generic capability versus exact project/tool usage),
  one-off upload wording/semantics, real deployment isolation and 2–3 independent sessions.
- Use `docs/release-readiness-checklist.md` for hosting, backup/recovery, OAuth/Gmail, helper,
  accessibility and participant steps. No new dependency or large refactor was needed here.
