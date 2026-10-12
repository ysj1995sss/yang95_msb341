# Independent review and live Streamlit recovery — 2026-10-11

## Scope and result

Continues the specs-016–018 experiment. The builder requested completion of the interrupted
independent review, recovery of the model's no-answer batch job, and actual Streamlit
background/Stop/Continue/process-restart checks with synthetic data.

Branch: `codex/truthful-tailoring-sources-publication`; main remains `a993491`.
Code follow-up: `e92d9e6`. No merge, push, new account, provider, dependency or deployment.
Both frontends and local Claude settings were preserved. Human participants: **0**.

The independent reviewer approved the code after additional RED/GREEN fixes. The original
API batch and the Streamlit test batch both finished **2 done / 0 failed** with four readable,
passing, one-page PDFs. That final outcome includes retries: **two real Word-file cleanup
failures occurred and remain an unresolved reliability risk**, not a clean first-attempt pass.

## Independent review timeline

The existing read-only reviewer resumed after the earlier spending-cap interruption. No
second review seat, spending-limit increase or cap workaround was used. It reviewed
`a993491..e2b3754`, then the working-tree follow-ups, without editing source, settings or Git.

It found four important gaps (no critical findings):

1. A summary skill listing could become activity at an already-named employer when the verb
   was outside the small action-word list, e.g. `spearheaded`. The guard now compares non-list
   context, permitting known-term reordering while rejecting new surrounding claims. A further
   review found bare comma-list summaries lacked the listing lead-in; that reproduction was
   also fixed. Existing actual-activity descriptions have a positive compatibility control.
2. Listed Rust was not in the shared named-tool set, although the term matcher recognized it.
   Rust and Swift now participate in claim-local protection even without posting evidence.
3. A lowercase unknown product following `analytics software/tools` disappeared into generic
   evidence. These explicit objects now stay Check yourself. Live testing then exposed the
   converse: `any platform unless ...` invented product names. A caution control prevents that.
   Supplemental review caught a determiner regression (`The Trade Desk`, `The NebulaForms`);
   the usage parser now skips the determiner while inspecting the following object.
4. Streamlit could launch/Continue/redo a master-resume batch with an active one-off upload.
   The shared Streamlit action boundary now refuses it and names the removal control in Tailor.

The main agent reproduced each reported behavior before changing production code. Intermediate
test failures were not hidden: the first focused run was 8 failed/36 passed, including a mistaken
assertion that excluded legitimate Reporting evidence; the assertion was corrected. A final-PDF
test initially omitted its actual SUMMARY heading and was corrected. An unelevated focused run
also had one scratch-folder permission error; the normal reviewed invocation with a fresh folder
resolved it. Compatibility REDs and the later bare-list/caution/determiner REDs preceded their fixes.

Final combined focused run: **84 passed, exit 0**. The reviewer independently observed 47
claim/source-focused tests and, on the last parser delta, **38 requirement tests**, exit 0.
Its final verdict was approval with no remaining critical or important code-review findings.
It did not independently run the full suites or live browser/model exercise. Its approval
explicitly excludes the unresolved Word cleanup issue, deployment and human usability.

## Verification

Final code at `e92d9e6`, standard local environments, fresh scratch directories:

- Product: **1329 passed, 1 skipped**, 87.26 seconds, exit 0 (post-code-commit rerun).
- API: **148 passed, 282 warnings**, 47.68 seconds, exit 0 (post-code-commit rerun). Existing deprecations are retained.
- Web lint and types: both exit 0.
- Playwright: **23 passed**, 1.2 minutes, exit 0.
- Diff whitespace check: exit 0.

The browser regression suite uses real UI/API/storage with simulated board/model/converter
boundaries; it is not live-model evidence. No Linux/remote CI was run on this unpushed branch.
Both post-code-commit exits were read before the final documentation commit.

## Real model and original failed batch

Used only the already-configured `codex-cli` integration, with `LLM_FALLBACK_MODELS=none` and
`LITELLM_MODE=PRODUCTION`. The synthetic connection probe returned READY, CLI exit 0.
Diagnostics were limited to allowlisted category flags; raw child output, credentials and
configuration were not printed or committed. A marker in successful CLI stderr is not proof
of authentication or quota failure.

In the actual Next.js browser on port 3303/API 8303, **Continue batch (1 left)** recovered
the original `a422ac91` batch in the existing ignored synthetic workspace. Both items finished;
the newly completed review opened and showed a passing one-page PDF. No model response was
fabricated, no fallback model was purchased, and the model bridge itself was not changed.

The earlier no-answer failure's subprocess diagnostics were not retained. Its underlying cause
could not be established or reproduced in this session. Report it as **operationally recovered
by retry/Continue**, not a proven root-cause fix or a guarantee it cannot recur.

## Actual Streamlit exercise

Normal app, port 8503, explicit ignored `product/.venv/tmp-codex/fix016-018/streamlit-live` data.
Only the repository's synthetic resume/profile and two invented pasted jobs were used. Search
goals and Save actions were seeded in that scratch workspace to reach its saved-job picker;
no external board search, real resume or employer submission was performed.

All model responses and Microsoft Word conversions were real. A temporary ignored launcher
logged only batch-button delivery and allowlisted model exit categories; it did not replace
responses or change app/runner behavior. It was removed from the running setup afterward.

1. The first two-job batch `b709a2d5` ran in the background. One job failed at temporary DOCX
   cleanup (WinError 32); the other published. Continue recovered it to 2/2.
2. Fresh batch `e88a82b2`: the browser showed Reporting Analyst running and Data Analyst waiting.
   **Stop after the current job** reached the real runner. The current job finished/published;
   the queued job became skipped/resumable. Disk state was cancelled, 1 done/1 skipped.
3. Career Profile remained usable while background work drained. This is agent-operated UI
   evidence, not a human usability session. Short browser snapshots initially showed stale
   intermediate state; ignored button diagnostics established delivery and actual disk state.
4. Continue started the skipped job. Once the batch was actively running under execution
   `073624539cba42dca3c8da1d3b60cb0b`, only its validated synthetic Streamlit worker was terminated.
   No unrelated app, model allowance, account or Word process was stopped.
5. A new Streamlit process on the same folder displayed: `This batch stopped before it finished
   (the app restarted). Continue it to tailor the rest.` The completed job stayed done, the
   interrupted job became Not started, and Continue remained available.
6. The first post-restart Continue returned a real model answer but hit the same DOCX cleanup
   error. A further Continue succeeded: final execution `d593183575c249bc87e3fd89457adf50`, 2 done,
   0 failed. The completed Reporting Analyst review's file hash stayed exactly
   `6a3037d1349c63ce003822d15a572c856623e522ca7736b111babef3b99fefc3`
   across interruption, recovery failure and final completion.

Read-only final artifact verification decoded the real saved reviews, required PASS validation,
matched saved PDF bytes to their published content-addressed files, extracted nonempty text
and counted one page each. All four PDFs are 61,212 bytes. Final SHA-256:

- API Data Analyst: `61917f12edbf0bf228e423e05074cda92cbdaa8bbb41e3c70f387e8c9819be5e`.
- API Reporting Analyst: `27968b40a26f25af5aa43dc6904e6054cf95ecb3a70c54a8005fd62cb4d3b767`.
- Streamlit Reporting Analyst: `719029239d421183a0d188b3fd0b10de710967971d19dcf59a303a1e2f3c7b5a`.
- Streamlit Data Analyst: `415e59c7f089825cf43aae9ddc467ddaeae5ea9e777456844f2c63e2523eae87`.

The model again proposed no meaningful edits for this small fixture. These are workflow,
publication and negative-control checks, not evidence of improved writing quality.

Proof screenshots are outside the repository in the allowed visualization output folder:
`job-copilot-streamlit-restarted.jpg` (restart note and remaining job) and
`job-copilot-streamlit-completed.jpg` (2/2 complete, passing review). The normal final server
was reloaded in the browser and its completed state verified after restart.

## Remaining release risk and next work

Two live failures originated at `docx_export/pipeline.py:finalize_docx_edits` while leaving its
TemporaryDirectory: Windows would not remove `tailored.docx` because it was still in use.
The model answered normally. Failed attempts preserved the previous review/artifact and stayed
resumable, but successful retries do not fix the underlying Word/document lifetime problem.

Next: write/review a bounded spec for exception-safe Word conversion and temporary-file cleanup.
Inspect ownership of documents/converter sessions; do not kill the user's Word processes or
hide errors with blanket ignored cleanup. The exact lock holder has not been proven. Keep this
risk open until deterministic failure tests and real repeated conversions/restart runs pass.

Independent code review and the requested live recovery exercise are now completed with the
above limits. Release readiness still requires resolving conversion reliability, human P01–P03
sessions, manual accessibility and account-dependent checklists. Both synthetic app servers were
restarted on the final code, with the normal uninstrumented Streamlit launcher. No integration,
push or production release is claimed.
