# Spec 021: Retire the Streamlit app

**Status:** Approved and implemented (2026-10-12). Correction to the facts below: `ui/__init__.py` imported the Streamlit shell, so the backend did load Streamlit indirectly until this change. Also removed: the Streamlit stylesheet in `ui/design_system.py` and its tests. Kept: `packages.txt` (CI installs LibreOffice from it). 67 test cases removed; all suites pass.
**Builds on:** decision 043 (the website is the product; Streamlit retired now).

## Goal

Remove the Streamlit app so there is one product to build, test and fix. The website
(`apps/web`) and its backend (`apps/api`) must keep working exactly as before. The old app stays
recoverable from the git tag `ui-streamlit-v1`, and from this branch's history.

## Facts checked (2026-10-12)

- **Streamlit users:** exactly 12 source files import Streamlit. The backend imports none of them,
  directly or indirectly. The shared modules the backend uses (17 files in `ui/`, plus
  `job_search/ui_helpers.py`, `applications/ui_helpers.py` and the engine) never import
  Streamlit.
- **Tests:** 14 of the 127 product test files touch Streamlit or its `AppTest` runner. Some
  mix Streamlit-page tests with tests of shared logic.

## What gets deleted

- **The Streamlit app:** `product/resume_tailorer/app.py` and all of `product/resume_tailorer/pages/`.
- **Streamlit-only screens:**
  - `ui/shell.py`, `ui/auth_gate.py`, `ui/batch_panel.py`, `ui/goals_wizard.py` and
    `ui/ats_panel.py`;
  - `applications/streamlit_views.py`.
- **Other modules nothing else uses** once those are gone, found by checking imports, not
  guessed. One example is `code_freshness.py`, which only existed to pick up Streamlit Cloud
  redeploys. The commit message lists every removed file.
- **Streamlit config:** `product/.streamlit/`, a stray `streamlit.log`, and the `streamlit`
  line in `product/requirements.txt`. Anything still importing Streamlit after the deletions
  fails the test run.
- **Tests:** Streamlit-page tests (`AppTest`) are deleted. In mixed files, only the Streamlit
  tests go and the shared-logic tests stay. The count before and after is reported.

## What stays

- **The engine and shared modules:** everything under `product/resume_tailorer/` that the backend
  uses (tailoring, review decisions, batches, checks, job search, profile, and the shared `ui/`
  logic modules). The folder name `ui/` stays for now; renaming it would be churn.
- **The website and backend:** unchanged.
- **The batch runner** keeps its cross-process lock, even though only one app uses it now.

## Docs

- **`AGENTS.md`, `CLAUDE.md` and both handoffs:** say Streamlit is retired, and point to the tag.
- **Decision records** stay as history; they aren't rewritten.
- **`CONTEXT.md`:** no change.

## Not done here (needs the builder)

- **The live demo** at `yang95msb341-…streamlit.app` redeploys whenever `main` is pushed. Once
  this lands on `main`, that demo breaks. Turning it off happens in the builder's Streamlit Cloud
  account; I won't touch it.
- **No push or merge** is part of this spec.

## Verification

- **Suites:** the product suite (minus the removed Streamlit tests), the API suite, web lint and
  types, and the full Playwright suite all pass with exit 0. Counts are reported before and after.
- **Leftover check:** a search shows no remaining `import streamlit` in the source.
- **A fresh-install check:** the backend imports and starts on a Python environment without
  Streamlit installed.

## Size

It's one commit, with deletions only, plus test and doc edits. Nothing new is added.
