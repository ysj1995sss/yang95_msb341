# Job Copilot UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a distinctive, accessible five-workspace Streamlit interface that makes every job match, resume edit, and application state traceable to verified evidence.

**Architecture:** Add a shared presentation layer under `resume_tailorer/ui/` for semantic tokens, navigation, page framing, and pure view models. Keep all existing product/domain logic unchanged; thin Streamlit pages consume the shared presentation layer. Split the combined Applications page into an Apply Launchpad and Application Tracker while preserving session handoffs and database behavior.

**Tech Stack:** Python 3.12+, Streamlit 1.41+, CSS injected through `st.markdown`, pytest, existing product/application services.

**Spec:** `specs/004-job-copilot-ui-redesign.md`

## Global Constraints

- `product/resume_tailorer/` remains the source of truth; UI code must not duplicate scoring, tailoring, validation, persistence, or submission logic.
- No new dependency or frontend framework.
- Preserve DOCX/PDF PASS/WARNING/FAIL gates and `ATSCapability.final_submission` safety behavior.
- Preserve Job Discovery -> Tailoring Studio and Tailoring Studio -> Apply handoffs.
- Use semantic colors exactly: ink `#17202A`, action `#2457D6`, verified `#187A57`, review `#B86E12`, blocked `#B33A3A`, canvas `#F5F7FA`, paper `#FFFFFF`, line `#D9E0E8`.
- Use Atkinson Hyperlegible with a system-sans fallback; resume artifacts retain their own typography.
- Labels and actions use sentence case; Candidate Fit and Resume Alignment remain separate.
- Existing user-owned edits in `AGENTS.md` and `HANDOFF-TO-CODEX.md` stay untouched.
- Use anonymized or synthetic data for browser verification.

## Review Focus

- A fresh session with no profile/job/artifact must show a useful next action rather than an empty dashboard; Task 1 tests `build_workflow_state({})` and Tasks 2-6 render those states.
- A WARNING artifact must remain reviewable but cannot look application-ready; Task 3 tests the semantic state mapping.
- Unknown Candidate Fit, salary, or sponsorship must render as “Not assessed”/“Not stated,” never zero; Task 1 tests display helpers and Task 4 uses them.
- A platform with `final_submission=False` must keep the real-submit action disabled after the redesign; Task 5 retains and tests the capability-gate view model.
- Narrow screens must stack Tailoring Studio review before preview without hiding actions; Task 6 verifies the responsive CSS and browser layout.

---

### Task 1: Shared visual tokens, workflow state, and navigation metadata

**Files:**
- Create: `product/resume_tailorer/ui/design_system.py`
- Create: `product/resume_tailorer/ui/shell.py`
- Create: `product/tests/test_ui_design_system.py`
- Modify: `product/resume_tailorer/ui/__init__.py`

**Interfaces:**
- Produces `WORKSPACES`, `semantic_status(status)`, `display_optional(value, empty_label)`, `build_workflow_state(session)`, `render_app_shell(active, workflow_state)`, `render_page_header(title, description, action_label=None)`.
- Consumes only mapping/string values and Streamlit at render time.

- [ ] **Step 1: Write failing pure-helper tests**

```python
def test_empty_session_starts_at_fact_vault():
    state = build_workflow_state({})
    assert [step.state for step in state] == ["current", "pending", "pending", "pending"]

def test_warning_is_review_not_ready():
    assert semantic_status("WARNING").label == "Review required"
    assert semantic_status("WARNING").application_ready is False

def test_unknown_value_is_not_zero():
    assert display_optional(None, "Not assessed") == "Not assessed"
```

- [ ] **Step 2: Run red test**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_ui_design_system.py -q --basetemp=.codex-pytest-ui-task1 -p no:cacheprovider`

Expected: import failure for `resume_tailorer.ui.design_system`.

- [ ] **Step 3: Implement immutable presentation models and theme CSS**

Define frozen `Workspace`, `WorkflowStep`, and `SemanticStatus` dataclasses. `WORKSPACES` must name Fact Vault, Job Discovery, Tailoring Studio, Apply Launchpad, and Application Tracker with their existing/new page paths. `render_app_shell` injects one scoped stylesheet containing the approved tokens, Atkinson import/fallback, focus-visible rules, reduced-motion behavior, responsive breakpoints, hidden default Streamlit navigation, custom `st.page_link` navigation, and the evidence ribbon.

- [ ] **Step 4: Run focused tests**

Run the Task 1 command; expected PASS.

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/ui product/tests/test_ui_design_system.py
git commit -m "feat: add Job Copilot interface system"
```

### Task 2: Fact Vault workspace

**Files:**
- Modify: `product/resume_tailorer/pages/1_Profile_Review.py`
- Create: `product/resume_tailorer/ui/fact_vault.py`
- Create: `product/tests/test_fact_vault_ui.py`

**Interfaces:**
- Consumes existing profile and verification dictionaries.
- Produces `build_fact_vault_summary(profile, verification) -> FactVaultSummary` and renders existing API operations without changing their contracts.

- [ ] **Step 1: Write failing summary tests**

```python
def test_summary_counts_verified_facts_and_user_edits():
    summary = build_fact_vault_summary(PROFILE, {"skills[0]": "user_verified"})
    assert summary.skill_count == len(PROFILE["skills"])
    assert summary.user_edit_count == 1
    assert summary.has_profile is True
```

- [ ] **Step 2: Run red test**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_fact_vault_ui.py -q --basetemp=.codex-pytest-ui-task2 -p no:cacheprovider`

- [ ] **Step 3: Implement and render**

Create the pure summary model. Apply the shared shell, replace numbered headers with a clear page header and staged upload/review regions, display a verification summary strip, use expanders per role, and retain every existing API call, form key, upload action, save action, and verification badge meaning.

- [ ] **Step 4: Run focused tests and existing profile API-client tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_fact_vault_ui.py tests/test_profile_review_api_client.py -q --basetemp=.codex-pytest-ui-task2 -p no:cacheprovider`

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/pages/1_Profile_Review.py product/resume_tailorer/ui/fact_vault.py product/tests/test_fact_vault_ui.py
git commit -m "feat: redesign profile review as Fact Vault"
```

### Task 3: Tailoring Studio workspace

**Files:**
- Modify: `product/resume_tailorer/app.py`
- Modify: `product/resume_tailorer/ui/artifact_review.py`
- Create: `product/resume_tailorer/ui/tailoring_view.py`
- Create: `product/tests/test_tailoring_view.py`
- Modify: `product/tests/test_artifact_review_ui.py`

**Interfaces:**
- Consumes existing `ArtifactPipelineResult`, `FinalApplicationReport`, `ResumeChange`, session keys, and regeneration helpers.
- Produces `build_tailoring_summary(state) -> TailoringSummary`, `group_changes(changes) -> ChangeGroups`, and split-layout rendering.

- [ ] **Step 1: Write failing view-model tests**

```python
def test_candidate_fit_and_alignment_stay_separate():
    summary = build_tailoring_summary(ARTIFACT_STATE)
    assert summary.candidate_fit.label == "Candidate fit"
    assert summary.resume_alignment.label == "Resume alignment"

def test_missing_requirements_never_enter_change_deck():
    groups = group_changes(CHANGES_WITH_TRUE_GAP)
    assert groups.true_gaps == ("GraphQL",)
    assert all("GraphQL" not in c.proposed_text for c in groups.reviewable)
```

- [ ] **Step 2: Run red test**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_tailoring_view.py tests/test_artifact_review_ui.py -q --basetemp=.codex-pytest-ui-task3 -p no:cacheprovider`

- [ ] **Step 3: Implement split studio and evidence deck**

Keep current pipeline execution and regeneration unchanged. Replace the initial empty screen with a focused setup panel. Once results exist, render reviewable changes on the left and report/download surface on the right. Every change shows original, proposed, requirement, evidence, reason, and validation state. Render true gaps in “Missing, never added.” Use consistent actions: Accept edit, Edit manually, Keep original. Keep advanced diff collapsed.

- [ ] **Step 4: Run focused artifact and tailoring tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_tailoring_view.py tests/test_artifact_review_ui.py tests/test_artifact_regeneration.py tests/test_artifact_pipeline.py -q --basetemp=.codex-pytest-ui-task3 -p no:cacheprovider`

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/app.py product/resume_tailorer/ui/artifact_review.py product/resume_tailorer/ui/tailoring_view.py product/tests/test_tailoring_view.py product/tests/test_artifact_review_ui.py
git commit -m "feat: build evidence-first Tailoring Studio"
```

### Task 4: Job Discovery workspace

**Files:**
- Modify: `product/resume_tailorer/pages/2_Job_Search.py`
- Modify: `product/resume_tailorer/job_search/ui_helpers.py`
- Create: `product/tests/test_job_discovery_ui.py`

**Interfaces:**
- Consumes existing `JobPosting`, `CandidateFitResult`, quality results, filters, and actions.
- Produces `build_job_card_view(job, fit, quality, action) -> JobCardView` with explicit unknown values and evidence lists.

- [ ] **Step 1: Write failing job-card tests**

```python
def test_unknown_fields_are_honest():
    card = build_job_card_view(JOB_WITH_UNKNOWNS, None, UNKNOWN_QUALITY, None)
    assert card.fit == "Not assessed"
    assert card.compensation == "Not stated"
    assert card.sponsorship == "Not stated"
```

- [ ] **Step 2: Run red test**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_job_discovery_ui.py -q --basetemp=.codex-pytest-ui-task4 -p no:cacheprovider`

- [ ] **Step 3: Implement workbench feed**

Apply the shared shell. Put search criteria in a compact sidebar/filter region and keep results primary. Render source disclosure before search. Replace generic expanders with structured job records containing match breakdown, gaps, quality, and clear Save/Pass/Tailor actions. Preserve all search, database, filter, and handoff calls.

- [ ] **Step 4: Run dashboard/search tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_job_discovery_ui.py tests/test_job_search_ui_helpers.py tests/test_job_search_dashboard.py tests/test_job_search_triage_handoff.py -q --basetemp=.codex-pytest-ui-task4 -p no:cacheprovider`

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/pages/2_Job_Search.py product/resume_tailorer/job_search/ui_helpers.py product/tests/test_job_discovery_ui.py
git commit -m "feat: redesign Job Discovery feed"
```

### Task 5: Apply Launchpad and Application Tracker split

**Files:**
- Create: `product/resume_tailorer/applications/streamlit_views.py`
- Modify: `product/resume_tailorer/pages/3_Applications.py`
- Create: `product/resume_tailorer/pages/4_Application_Tracker.py`
- Create: `product/tests/test_application_workspace_ui.py`

**Interfaces:**
- Consumes existing `JobService`, `ATSCapability`, `StatusTracker`, filters, sorters, and session handoffs.
- Produces `build_launchpad_state(...) -> LaunchpadState`, `render_apply_launchpad(service)`, and `render_application_tracker(service)`.

- [ ] **Step 1: Write failing safety-state tests**

```python
def test_unproven_platform_recommends_manual_and_disables_submit():
    state = build_launchpad_state(mode=ApplicationMode.ASSIST, capability=UNPROVEN)
    assert state.recommended_mode is ApplicationMode.MANUAL
    assert state.real_submit_enabled is False
    assert state.primary_action == "Open application"
```

- [ ] **Step 2: Run red test**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_application_workspace_ui.py -q --basetemp=.codex-pytest-ui-task5 -p no:cacheprovider`

- [ ] **Step 3: Extract existing behavior and create two thin pages**

Move rendering functions without changing domain calls. Page 3 becomes Apply Launchpad with Manual mode first, a staged-assets checklist, concise capability disclosure, Preview, and Open application as the primary safe action. Page 4 becomes Application Tracker with saved views, filters, detail, next action, provenance, and status update.

- [ ] **Step 4: Run safety and dashboard tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_application_workspace_ui.py tests/test_application_ui_helpers.py tests/test_submission_engine.py tests/test_ats_capabilities.py -q --basetemp=.codex-pytest-ui-task5 -p no:cacheprovider`

- [ ] **Step 5: Commit**

```bash
git add product/resume_tailorer/applications/streamlit_views.py product/resume_tailorer/pages/3_Applications.py product/resume_tailorer/pages/4_Application_Tracker.py product/tests/test_application_workspace_ui.py
git commit -m "feat: split Apply Launchpad and Application Tracker"
```

### Task 6: Responsive browser verification, critique, and documentation

**Files:**
- Modify: `product/resume_tailorer/ui/design_system.py`
- Modify: `README.md`
- Create: `decisions/019-job-copilot-evidence-workbench-ui.md`

**Interfaces:**
- Consumes all five completed workspaces.
- Produces the final responsive CSS, documented public UI state, and design decision record.

- [ ] **Step 1: Run both complete suites**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest -q --basetemp=.codex-pytest-ui-final -p no:cacheprovider`

Run: `cd apps/api; .\.venv\Scripts\python.exe -m pytest -q --basetemp=.codex-pytest-ui-final -p no:cacheprovider`

- [ ] **Step 2: Launch the application and verify all workspaces at desktop width**

Use synthetic session/database data. Capture screenshots of Fact Vault, Job Discovery, Tailoring Studio, Apply Launchpad, and Application Tracker. Verify navigation, empty states, evidence labels, safety gates, and workflow handoffs.

- [ ] **Step 3: Verify at 390px mobile width and keyboard focus**

Confirm review content precedes preview, actions remain visible, records do not clip, navigation remains operable, and focus outlines are visible. Confirm reduced-motion CSS disables nonessential transitions.

- [ ] **Step 4: Critique against the frontend brief and remove one unnecessary treatment**

Check for generic identical cards, decorative gradients, all-caps labels, excessive rounded corners, redundant labels, and inconsistent semantic colors. Fix any finding and rerun the affected focused tests.

- [ ] **Step 5: Record the decision and update README interface description**

Decision 019 documents the evidence-workbench concept, preserved architecture, five-workspace mapping, accessibility, verification results, and honest limitations. README names the five workspaces and links the live app when available; it must not invent a deployment URL.

- [ ] **Step 6: Final verification and commit**

Run both complete suites again after critique, then:

```bash
git add product/resume_tailorer/ui/design_system.py README.md decisions/019-job-copilot-evidence-workbench-ui.md
git commit -m "docs: close Job Copilot UI redesign"
```

## Execution decision

Use **Native execution** in the current session. The tasks share one evolving presentation contract and must preserve user-owned working-tree edits. After Task 6, request one whole-branch review, adjudicate confirmed findings, rerun both full suites, and only then report completion.
