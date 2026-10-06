# Spec 012A: Complete Word Profile Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Work directly in this session; do not dispatch subagents.

**Goal:** Sync identifiable, resume-bearing Career Profile facts into a copy of the person's Word resume without silently delivering stale contradictory facts.

**Architecture:** Keep `sync_docx_to_profile(docx_bytes, profile)` as the public entry point. Put paragraph/section locating and field rewriting in a small `docx_export/profile_fields.py` helper, while `profile_sync.py` owns matching, reporting and orchestration. `tailoring_service.py` refuses a distributable Word artifact when the sync reports a blocking contradiction; both frontends already display `sync_summary` returned by the shared API/service.

**Tech Stack:** Python 3.14, python-docx, pytest; FastAPI `/v2` adapter, Next.js 16/Playwright, retained Streamlit.

**Spec:** `specs/012-complete-profile-sync-and-freeform-review.md` (part A)

## Global Constraints

- No new dependency, account, deployment, paid model or real user data.
- Keep the original DOCX; update a copy, preserve layout and unchanged paragraph/run XML, and return identical bytes when nothing changed.
- Match roles and education only when identity is unambiguous; never guess a target paragraph.
- The stored Career Profile and provenance must not be reordered or overwritten.
- Keep `review_store` format 2, existing `/v2` and legacy API fields, truthfulness/length/readability gates, and the no-submission gate.
- Tests use synthetic people and jobs only. Use no real folders, names, emails, phone numbers or API keys.
- On the builder's Windows PC, use the existing `product/.venv` and `apps/api/.venv`; run all three suites and one supervised real-model run before claiming done.

## Review Focus

1. Two roles at the same employer with one renamed title: Task 1 test must refuse an uncertain cross-role match and report it.
2. A missing summary or skills section: Task 2 test must report the unplaced fact, without inserting it in an unrelated section.
3. Contact data in a Word header/footer: Task 2 test must either locate a unique line there or report it; the existing readability warning remains.
4. Two education entries at the same institution: Task 3 test must not swap degrees or dates.
5. A contradictory old title/date: Task 4 test must stop the artifact before Apply can receive a passing handoff.

## File map

- Create `product/resume_tailorer/docx_export/profile_fields.py`: section-aware paragraph targets, safe in-place text rewrite, contact/summary/skills/education/certification placement helpers.
- Modify `product/resume_tailorer/docx_export/profile_sync.py`: `SyncField`/`SyncResult` diagnostics, one-to-one matching and orchestration, existing bullet logic retained.
- Modify `product/resume_tailorer/parsers/docx_structure.py` only if a structural target cannot be found without adding an inconsistent second parser.
- Modify `product/resume_tailorer/tailoring_service.py`: fail closed for blocking sync mismatches; keep `sync_summary` and synced bytes in run state.
- Modify `product/tests/test_profile_sync.py` and add focused integration tests in `product/tests/test_tailoring_service.py`.
- Add an API assertion in `apps/api/tests/test_workspace_tailor.py` and a browser assertion in `apps/web/e2e/journey.spec.ts` for the existing shared sync message/error.
- Create `decisions/034-complete-profile-sync-and-freeform-review.md` and `discovery/experiments/2026-10-spec-012-supervised-runs.md` after the behavior is verified.

## Task 1: Structured diagnostics and safe role identity

**Files:** `product/resume_tailorer/docx_export/profile_sync.py`; `product/tests/test_profile_sync.py`.

**Interfaces:** `SyncField(field: str, value: str, outcome: str, reason: str = "", blocking: bool = False)`; `SyncResult.fields: list[SyncField]` defaults to an empty list; `SyncResult.has_blockers: bool`. `sync_docx_to_profile` keeps its existing signature and returns the same result type.

- [ ] **Step 1: Write failing tests** for a unique employer/title correction and an ambiguous duplicate-employer case. Extend the synthetic `_docx()` and `_profile()` helpers rather than adding real data.

  ```python
  def _docx_two_acme_roles():
      doc = Document(io.BytesIO(_docx()))
      heading = next(p for p in doc.paragraphs if p.text == "EDUCATION")
      heading.insert_paragraph_before("Sales Analyst")
      heading.insert_paragraph_before("Acme Retail | Jan 2020 - Dec 2021")
      out = io.BytesIO()
      doc.save(out)
      return out.getvalue()

  def _profile_two_acme_roles_renamed():
      profile = _profile([A1, A2, A3])
      acme = profile.work_experience[1]
      acme.title = "Senior Marketing Analyst"
      acme.dates = "Jan 2023 - Present"
      profile.work_experience.append(WorkExperience(
          employer="Acme Retail", title="Sales Analyst", dates="Jan 2020 - Dec 2021",
          responsibilities=[], accomplishments=[]
      ))
      return profile

  def test_unique_employer_title_edit_updates_the_existing_role():
      profile = _profile([A1, A2, A3])
      profile.work_experience[1].title = "Senior Marketing Analyst"
      result = sync_docx_to_profile(_docx(), profile)
      assert "Senior Marketing Analyst" in _texts(result.docx_bytes)
      assert "Marketing Analyst" not in _texts(result.docx_bytes)
      assert any(f.field == "work.title" and f.outcome == "updated" for f in result.fields)

  def test_two_roles_at_one_employer_do_not_guess_a_renamed_title():
      result = sync_docx_to_profile(_docx_two_acme_roles(), _profile_two_acme_roles_renamed())
      assert result.has_blockers
      assert any(f.field == "work.title" and "ambiguous" in f.reason.lower() for f in result.fields)
  ```

- [ ] **Step 2: Run the two tests and see them fail** with missing `fields`/`has_blockers` or unchanged title. Run from `product/`: `./.venv/Scripts/python.exe -m pytest tests/test_profile_sync.py -q -k 'unique_employer_title or two_roles_at_one_employer' -p no:cacheprovider`.
- [ ] **Step 3: Implement the diagnostic model and matching policy.** Exact normalized employer+title has priority; only a unique employer with a non-conflicting date anchor can match a renamed title; two plausible roles produce a blocking `SyncField` and no rewrite. Keep `aligned_profile` in file order as today.

  ```python
  @dataclass(frozen=True)
  class SyncField:
      field: str
      value: str
      outcome: str  # "updated" | "unplaced"
      reason: str = ""
      blocking: bool = False

  # Add to SyncResult after its existing bullet counters:
  fields: list[SyncField] = field(default_factory=list)

  @property
  def has_blockers(self) -> bool:
      return any(item.blocking for item in self.fields)
  ```

- [ ] **Step 4: Run `tests/test_profile_sync.py` in full.** Keep all existing bullet-order, typed-bullet and byte-identical no-op tests green.
- [ ] **Step 5: Commit only this independently testable role/diagnostic increment** after approval of this plan: `git add product/resume_tailorer/docx_export/profile_sync.py product/tests/test_profile_sync.py` and `git commit -m "feat: match Word profile roles safely and report sync gaps"` with the builder's required co-author trailer.

## Task 2: Contact, summary, skills and tools in the existing layout

**Files:** create `product/resume_tailorer/docx_export/profile_fields.py`; modify `profile_sync.py`, perhaps `parsers/docx_structure.py`; test `product/tests/test_profile_sync.py`.

**Interfaces:** `sync_simple_fields(doc: Document, profile: CareerTruthProfile) -> list[SyncField]` locates unique contact, summary, skills/tools targets and rewrites in place. It never adds a new section. The caller adds its diagnostics to `SyncResult.fields` and saves bytes only when at least one paragraph changed.

- [ ] **Step 1: Write failing tests** with a synthetic document containing a summary paragraph, `SKILLS` heading and one skills line. Assert the old paragraphs keep their style, and that a document with no skills heading reports an unplaced skills field.

  ```python
  def test_summary_and_skills_reach_the_word_file_without_moving_paragraphs():
      profile = _profile([A1, A2, A3])
      profile.summary = "Marketing analyst focused on retail reporting"
      profile.skills = ["SQL", "Tableau"]
      doc = Document(io.BytesIO(_docx()))
      next(p for p in doc.paragraphs if p.text == "EXPERIENCE").insert_paragraph_before(
          "Old summary about retail reporting"
      )
      doc.add_paragraph("SKILLS")
      doc.add_paragraph("Skills: SQL")
      out = io.BytesIO()
      doc.save(out)
      original = out.getvalue()
      result = sync_docx_to_profile(original, profile)
      texts = _texts(result.docx_bytes)
      assert profile.summary in texts
      assert any("SQL" in text and "Tableau" in text for text in texts)
      assert texts.index("EXPERIENCE") < texts.index("EDUCATION")

  def test_missing_skills_section_is_reported_not_inserted_elsewhere():
      profile = _profile([A1, A2, A3])
      profile.skills = ["Tableau"]
      result = sync_docx_to_profile(_docx(), profile)
      assert any(f.field == "skills" and f.outcome == "unplaced" for f in result.fields)
      assert "Tableau" not in " ".join(_texts(result.docx_bytes))
  ```

- [ ] **Step 2: Run the new tests red.** Run `./.venv/Scripts/python.exe -m pytest tests/test_profile_sync.py -q -k 'summary_and_skills or missing_skills_section' -p no:cacheprovider` from `product/`.
- [ ] **Step 3: Implement section-aware targeting and the existing run-preserving rewrite.** Use `extract_docx_structure` for summary targets; recognize a uniquely labelled `SKILLS` or `Core Competencies` line/section for skills/tools; recognize unique email/phone/name lines in body or header/footer. Preserve label text. If a target has mixed unknown content, record `unplaced` instead of rewriting it wholesale. Do not touch a paragraph whose desired text equals its current text.

  ```python
  def rewrite_paragraph(paragraph, wanted: str) -> bool:
      if paragraph.text == wanted:
          return False
      keep = _marker_runs(paragraph)  # import from docx_export.splicer
      runs = paragraph.runs
      if keep and len(runs) > keep:
          target, rest = runs[keep], runs[keep + 1:]
      elif runs:
          target, rest = runs[0], runs[1:]
      else:
          paragraph.add_run(wanted)
          return True
      target.text = wanted
      for run in rest:
          run._element.getparent().remove(run._element)
      return True
  ```

- [ ] **Step 4: Add and run one header/footer contact test** that verifies a unique match is updated while the existing header-contact readability warning remains. Run all `test_profile_sync.py` tests green.

  ```python
  def test_unique_header_email_is_updated_without_moving_it():
      doc = Document(io.BytesIO(_docx()))
      doc.paragraphs[1].text = ""
      doc.sections[0].header.paragraphs[0].text = "riley.old@example.com"
      out = io.BytesIO()
      doc.save(out)
      profile = _profile([A1, A2, A3])
      profile.contact_info["email"] = "riley.new@example.com"
      result = sync_docx_to_profile(out.getvalue(), profile)
      changed = Document(io.BytesIO(result.docx_bytes))
      assert changed.sections[0].header.paragraphs[0].text == "riley.new@example.com"
      assert any(f.field == "contact.email" and f.outcome == "updated" for f in result.fields)
  ```
- [ ] **Step 5: Commit this field-sync increment** with the new helper, parser change if needed and tests; use a message such as `feat: sync Word summary skills and contact in place` plus the co-author trailer.

## Task 3: Education and certifications without cross-entry swaps

**Files:** `profile_fields.py`, `profile_sync.py`, `product/tests/test_profile_sync.py`.

**Interfaces:** Add `sync_education_and_certifications(doc, profile) -> list[SyncField]`; call it from `sync_docx_to_profile` after role/summary syncing. Unique institution+degree wins; unique institution may identify a corrected degree only when no other entry competes.

- [ ] **Step 1: Write failing tests** for a changed degree/year under one institution, two degrees at one institution, and a certification section that is absent.

  ```python
  def test_education_edit_stays_with_its_institution():
      profile = _profile([A1, A2, A3])
      profile.education[0].degree = "Bachelor of Science"
      profile.education[0].year = 2020
      result = sync_docx_to_profile(_docx(), profile)
      assert "Bachelor of Science" in " ".join(_texts(result.docx_bytes))
      assert "2020" in " ".join(_texts(result.docx_bytes))

  def test_duplicate_institution_does_not_swap_degrees():
      doc = Document(io.BytesIO(_docx()))
      doc.add_paragraph("MS Marketing, State University, 2021")
      out = io.BytesIO()
      doc.save(out)
      original = out.getvalue()
      profile = _profile([A1, A2, A3])
      profile.education = [
          EducationEntry("Bachelor of Science", "Economics", "State University", 2020),
          EducationEntry("Master of Science", "Marketing", "State University", 2022),
      ]
      result = sync_docx_to_profile(original, profile)
      assert result.has_blockers or any(f.outcome == "unplaced" for f in result.fields)
      assert _texts(result.docx_bytes).index("BS Economics, State University, 2019") < _texts(result.docx_bytes).index("MS Marketing, State University, 2021")

  def test_missing_certifications_section_reports_an_unplaced_credential():
      profile = _profile([A1, A2, A3])
      profile.certifications = ["PMP"]
      result = sync_docx_to_profile(_docx(), profile)
      assert any(f.field == "certifications" and f.outcome == "unplaced" for f in result.fields)
      assert "PMP" not in " ".join(_texts(result.docx_bytes))
  ```

- [ ] **Step 2: Run these tests red**, then implement unique section-bounded education/certification placement. Replace only identifiable fragments in a paragraph; preserve unrelated honors, GPA and run/paragraph styling. Report an absent or ambiguous section; do not create one.
- [ ] **Step 3: Run all profile-sync tests green** and inspect a synthetic DOCX's paragraph XML before/after to verify an untouched paragraph remains identical.
- [ ] **Step 4: Commit the education/certification increment** with its tests and the co-author trailer.

## Task 4: Fail closed at the tailoring boundary and show the report

**Files:** `product/resume_tailorer/tailoring_service.py`, `product/tests/test_tailoring_service.py`, `apps/api/tests/test_workspace_tailor.py`, `apps/web/e2e/journey.spec.ts`; use the existing `sync_summary` adapters unless tests prove a display gap.

**Interfaces:** `sync.has_blockers` raises `TailoringError` before `run_docx_tailoring_pipeline`; non-blocking `sync.summary` is retained in the state and existing `/v2/tailor` review response. No new API field is required.

- [ ] **Step 1: Write a failing product test** that supplies a Word file with an ambiguous, contradictory role title/date and asserts `TailoringError` occurs before the model or artifact handoff.

  ```python
  def test_ambiguous_stale_role_blocks_word_tailoring(monkeypatch, tmp_path):
      class FailIfCalled:
          def complete(self, system, user, max_tokens=2000):
              raise AssertionError("A blocked Word run must not call the model")

      session = {"artifacts_dir": str(tmp_path)}
      with pytest.raises(TailoringError, match="Word file"):
          run_tailoring(session, original_bytes=_docx_two_acme_roles(), filename="riley.docx",
                        job_description="Marketing analyst with SQL reporting experience",
                        pending={"job_id": "j1", "title": "Analyst", "company": "Acme"},
                        llm=FailIfCalled(), career_profile=_profile_two_acme_roles_renamed())
      assert not session.get("active_handoff")
  ```

- [ ] **Step 2: Run that test red**, then add the `sync.has_blockers` check immediately after `sync_docx_to_profile` in `run_tailoring`. The message must list field names/reasons and a safe next action; keep non-blocking placements in `sync_summary`.

  ```python
  if sync.has_blockers:
      detail = "; ".join(f"{item.field}: {item.reason}" for item in sync.fields if item.blocking)
      raise TailoringError(f"Your Word file could not be safely synced: {detail}. Edit the Word file or use a rebuilt layout.")
  ```

- [ ] **Step 3: Add one API test** asserting the `/v2` error is plain and no passing PDF/Apply handoff exists, plus one Playwright assertion in the current journey that the non-blocking sync message is visible. Keep both frontends using the existing shared message.
- [ ] **Step 4: Run the focused product/API tests and web lint/types/Playwright.** Commit this boundary increment with the co-author trailer.

## Task 5: End-to-end verification and decision record

**Files:** `decisions/034-complete-profile-sync-and-freeform-review.md`, `discovery/experiments/2026-10-spec-012-supervised-runs.md`, spec 012 status/checkboxes.

- [ ] **Step 1: Run the full product and API suites** with synthetic test data only. On this sandbox, set `TEMP`/`TMP` to a workspace directory and use `--basetemp`; the API venv currently needs the existing product venv's site-packages added to its import path for `bs4`.
- [ ] **Step 2: Run web lint, types and all Playwright tests.** Node is at `D:/Yang/Software/cursor/_bak/NodeJs`; the Next build may need network access for Google Fonts. Record exact counts, warnings and any unavailable check.
- [ ] **Step 3: Perform one supervised real-model Word run** with a synthetic DOCX containing changed title/date, summary, skills and education; exercise one ambiguous placement. Verify the resulting DOCX/PDF visually and by text extraction. Do not use the builder's real data or an employer site.
- [ ] **Step 4: Record evidence and rationale** in decision 034 and the experiment record. Mark only actually satisfied spec-012A checkboxes complete. Commit docs with the co-author trailer, then push to `main` and check CI only if the builder has approved this plan and the code/tests are green.

## Plan self-check

- Spec 012A coverage: role, contact, summary, skills/tools, education, certification, formatting, reporting, blocking, adapters and supervised verification are mapped to Tasks 1–5.
- No dependency or deployment step is introduced. Tasks 1–4 each yield a testable commit; Task 5 closes the evidence and CI loop.
