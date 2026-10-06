# Spec 012B: Free-Form Summary and Skills Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Work directly in this session; do not dispatch subagents.

**Goal:** Let a person independently accept, reject, restore or manually edit each PDF/free-form summary and skills change, with safe regeneration and the existing truthfulness gates.

**Architecture:** Extract summary and skills as section spans before the existing bullet comparison. Build section-specific `ResumeChange` rows with baseline offsets, while leaving `DiffGenerator._compute_changes`'s global greedy algorithm unchanged for work bullets. Regenerate new section changes from the saved baseline using validated spans in descending offset order; legacy bullet changes retain their current path. API and both UIs receive a shared section label.

**Tech Stack:** Python 3.14, pytest, PDFGenerator and the existing validators; FastAPI `/v2`, Next.js 16/Playwright and retained Streamlit.

**Spec:** `specs/012-complete-profile-sync-and-freeform-review.md` (part B). Execute plan 012A first; both plans share the final decision record and experiment file.

## Global Constraints

- No new dependency, account, deployment, paid model or real user data.
- Do not change `DiffGenerator._compute_changes` or weaken the existing global greedy matching, semantic-drift, fabrication, unsupported-term, length or readability checks.
- A new section edit cannot become an unsupported experience claim; unsafe AI and manual edits cannot produce a downloadable artifact.
- Regeneration uses the saved baseline and never re-invokes a model. A missing/ambiguous span fails visibly rather than replacing another occurrence.
- Keep `review_store` format 2, the legacy fixture, stored enum values, existing API fields, existing bullet change IDs and the no-submission gate.
- Both UIs use the same shared labels/view model. Tests use synthetic people, jobs, resumes and model stubs only.
- Run product, API and web suites and a supervised real-model PDF run before claiming done.

## Review Focus

1. The same phrase appears in both summary and work history: Task 3 test must change only the summary span.
2. A skills section wraps across lines or uses bullets: Tasks 1–2 tests must produce one skills change and no false empty bullet.
3. A section heading appears twice or cannot be found: Task 1 test must report ambiguity, not guess a span.
4. A legacy format-2 review has no new span field: Task 3 test must still load and regenerate with its old bullet behavior.
5. A manual section edit introduces a credential or duration not in confirmed evidence: Task 4 test must reject it before PDF regeneration.

## File map

- Create `product/resume_tailorer/artifacts/freeform_sections.py`: identify section spans, canonical profile section text and the source of the exact baseline offsets.
- Modify `product/resume_tailorer/artifacts/models.py`: one defaulted `baseline_span` on `ResumeChange`; no enum changes.
- Modify `product/resume_tailorer/artifacts/changes.py`: add section changes and keep work-bullet changes distinct.
- Modify `product/resume_tailorer/diff_generator.py` only to expose a comparison wrapper around the existing `_compute_changes`, not to alter that algorithm.
- Modify `product/resume_tailorer/artifacts/regeneration.py`: apply new span-addressed section changes safely; keep legacy bullets on the old path.
- Modify `product/resume_tailorer/tailoring_service.py`: pass review to manual validation and surface a clear error on ambiguous regeneration.
- Modify `product/resume_tailorer/ui/tailor_progress.py`: shared `change_section_label(change)` for both frontends.
- Modify `apps/api/app/workspace/tailor_router.py`, `apps/web/src/lib/types.ts`, `apps/web/src/app/tailor/review.tsx`, and `product/resume_tailorer/pages/5_Tailor.py` only for the additive section label.
- Test in `product/tests/test_freeform_sections.py`, `product/tests/test_review_persistence.py`, `product/tests/test_legacy_review_loads.py`, `product/tests/test_diff_generator.py`, `product/tests/test_tailoring_service.py`, `apps/api/tests/test_workspace_tailor.py`, and `apps/web/e2e/journey.spec.ts`.

## Task 1: Section spans and explicit ambiguity

**Files:** create `product/resume_tailorer/artifacts/freeform_sections.py`; create `product/tests/test_freeform_sections.py`.

**Interfaces:** `SectionSpan(name: str, start: int, end: int, text: str)` uses character offsets into the unmodified tailored text. `find_sections(text: str) -> dict[str, SectionSpan]` recognizes conventional summary and skills headings, including `PROFESSIONAL SUMMARY`, `SUMMARY`, `SKILLS`, `TECHNICAL SKILLS` and `CORE COMPETENCIES`. `SectionAmbiguity(ValueError)` names repeated or uncertain headings. `profile_section(profile, name) -> str` renders a truthful section from profile fields for rejection/restoration. `missing_section_anchor(text, name) -> int` locates a safe zero-length insertion point for a removed section.

- [ ] **Step 1: Write failing tests** for a normal two-section document, wrapped skills lines and a duplicate heading.

  ```python
  def test_summary_and_wrapped_skills_have_exact_spans():
      text = "Riley Park\nSUMMARY\nRetail analyst\nEXPERIENCE\n- Built SQL reports\nSKILLS\nSQL, Tableau,\nPower BI\nEDUCATION\nBS Economics\n"
      spans = find_sections(text)
      assert text[spans["summary"].start:spans["summary"].end].startswith("SUMMARY\n")
      assert "SQL, Tableau,\nPower BI" in spans["skills"].text
      assert "Built SQL reports" not in spans["skills"].text

  def test_duplicate_skills_heading_is_ambiguous():
      text = "SUMMARY\nAnalyst\nSKILLS\nSQL\nEXPERIENCE\n- Built reports\nSKILLS\nPython\n"
      with pytest.raises(SectionAmbiguity, match="skills"):
          find_sections(text)

  def test_wrapping_and_heading_alias_alone_are_not_a_skills_edit():
      profile = CareerTruthProfile(
          contact_info={"name": "Riley Park"}, education=[], work_experience=[],
          skills=["SQL", "Tableau"], tools=[], certifications=[], accomplishments=[], summary="",
      )
      text = "Riley Park\nTECHNICAL SKILLS\nSQL,\nTableau\n"
      changes = build_freeform_changes(profile, text, GapReport([], ""), review=None)
      assert not any(change.section == "skills" for change in changes)
  ```

- [ ] **Step 2: Run `tests/test_freeform_sections.py` red.** Run from `product/`: `./.venv/Scripts/python.exe -m pytest tests/test_freeform_sections.py -q -p no:cacheprovider`.
- [ ] **Step 3: Implement line-offset scanning.** Recognize headings only on complete lines, end each span at the next recognized heading, preserve original whitespace and offsets, and raise `SectionAmbiguity` on a duplicate target heading. `profile_section` renders `SUMMARY\n<profile.summary>\n` and `SKILLS\n<skills/tools terms>\n` only from profile data.

  ```python
  @dataclass(frozen=True)
  class SectionSpan:
      name: str
      start: int
      end: int
      text: str

  class SectionAmbiguity(ValueError):
      pass

  _TARGETS = {
      "SUMMARY": "summary", "PROFESSIONAL SUMMARY": "summary",
      "SKILLS": "skills", "TECHNICAL SKILLS": "skills", "CORE COMPETENCIES": "skills",
  }
  _BOUNDARIES = set(_TARGETS) | {"EXPERIENCE", "WORK EXPERIENCE", "EDUCATION", "CERTIFICATIONS", "PROJECTS"}

  def find_sections(text: str) -> dict[str, SectionSpan]:
      lines = text.splitlines(keepends=True)
      offsets = []
      position = 0
      for line in lines:
          offsets.append(position)
          position += len(line)
      headings = [(i, line.strip().upper()) for i, line in enumerate(lines)
                  if line.strip().upper() in _BOUNDARIES]
      found = {}
      for number, (i, heading) in enumerate(headings):
          name = _TARGETS.get(heading)
          if name is None:
              continue
          if name in found:
              raise SectionAmbiguity(f"More than one {name} section")
          start = offsets[i]
          end = offsets[headings[number + 1][0]] if number + 1 < len(headings) else len(text)
          found[name] = SectionSpan(name, start, end, text[start:end])
      return found

  def profile_section(profile, name: str) -> str:
      if name == "summary":
          return f"SUMMARY\n{profile.summary.strip()}\n" if profile.summary.strip() else ""
      terms = [term.strip() for term in [*profile.skills, *profile.tools] if term.strip()]
      return "SKILLS\n" + ", ".join(terms) + "\n" if terms else ""

  def missing_section_anchor(text: str, name: str) -> int:
      if name == "summary":
          offset = 0
          for line in text.splitlines(keepends=True):
              if line.strip().upper() in _BOUNDARIES:
                  return offset
              offset += len(line)
          raise SectionAmbiguity("Cannot place a removed summary without a section boundary")
      if name == "skills":
          for marker in ("\nEDUCATION\n", "\nCERTIFICATIONS\n"):
              position = text.find(marker)
              if position >= 0:
                  return position + 1
          return len(text)
      raise SectionAmbiguity(f"Unknown section: {name}")
  ```

- [ ] **Step 4: Run the section tests green** and add a case where `SQL` in work experience is not classified as a skills section.
- [ ] **Step 5: Commit the parser increment** after plan approval: `git add product/resume_tailorer/artifacts/freeform_sections.py product/tests/test_freeform_sections.py` and `git commit -m "feat: locate free-form summary and skills sections"` with the builder's co-author trailer.

## Task 2: Section-specific review changes; retain global work-bullet pairing

**Files:** `product/resume_tailorer/artifacts/models.py`, `artifacts/changes.py`, `diff_generator.py`; tests `product/tests/test_freeform_sections.py`, `test_diff_generator.py` and `test_review_persistence.py`.

**Interfaces:** `ResumeChange.baseline_span: tuple[int, int] | None = None` is additive/defaulted. New IDs are `freeform:summary:0` and `freeform:skills:0`; existing `freeform:<index>` bullet IDs are unchanged. `DiffGenerator.compare_bullets(original: list[str], tailored: list[str], profile: CareerTruthProfile) -> list[BulletChange]` delegates unchanged to `_compute_changes`.

- [ ] **Step 1: Write failing tests** using synthetic profile facts with a summary edit and wrapped skills. Assert exactly one change per section and no work-bullet change `SQL → (empty)`.

  ```python
  from resume_tailorer.analyzers.gap_analyzer import GapReport
  from resume_tailorer.models import CareerTruthProfile, WorkExperience

  def test_summary_and_wrapped_skills_are_separate_review_changes():
      profile = CareerTruthProfile(
          contact_info={"name": "Riley Park"}, education=[],
          work_experience=[WorkExperience("Acme Retail", "Analyst", "2022-Present",
                                          ["Built SQL reports"], [])],
          skills=["SQL", "Tableau"], tools=[], certifications=[], accomplishments=[],
          summary="Retail analyst",
      )
      text = "Riley Park\nSUMMARY\nRetail analyst focused on reporting\nEXPERIENCE\n- Built SQL reports\nSKILLS\nTableau,\nSQL\n"
      changes = build_freeform_changes(profile, text, GapReport([], ""), review=None)
      assert {c.change_id for c in changes if c.section in {"summary", "skills"}} == {
          "freeform:summary:0", "freeform:skills:0"
      }
      assert not any(c.original_text == "SQL" and not c.proposed_text for c in changes)
  ```

- [ ] **Step 2: Run the new tests red**, then add `baseline_span` to `ResumeChange` with a default and produce section changes from `find_sections`. `proposed_text` must be the exact `tailored_text[start:end]`; `original_text` must be `profile_section(profile, name)`. A missing target section with non-empty profile content is a removal change whose zero-length insertion position is determined by the neighboring conventional headings; if no safe position exists, surface `SectionAmbiguity`.

  Compare normalized content rather than presentation alone: summary whitespace and a synonymous heading do not create a change; skills line wraps and a synonymous heading do not create a change, but a changed term or term order does. Retain the exact proposed bytes for regeneration spans.

  ```python
  # Append this defaulted field to the existing ResumeChange dataclass:
  baseline_span: tuple[int, int] | None = None
  ```

- [ ] **Step 3: Keep bullet comparison section-scoped.** Pass only work/education bullets to `compare_bullets` and only text outside summary/skills spans as its tailored input, while passing the *full* profile to fabrication checks. Do not change `_compute_changes` or its tests. Assert the decision-018 Education/Skills regression fixtures still pair true bullets globally.
- [ ] **Step 4: Run all affected diff, free-form and persistence tests green.** Commit this independently reviewable change-builder increment with the co-author trailer.

## Task 3: Rebuild from section spans, not global first-match text

**Files:** `product/resume_tailorer/artifacts/regeneration.py`, `product/tests/test_review_persistence.py`, `product/tests/test_legacy_review_loads.py`.

**Interfaces:** `apply_dispositions_to_text(baseline_text, changes, profile=None)` keeps its signature. For changes with `baseline_span`, replace verified baseline slices in descending `start` order. For changes with `baseline_span is None`, preserve existing legacy bullet replacement/reinsertion behavior.

- [ ] **Step 1: Write failing tests** where summary and work bullet both contain `SQL`, plus accept/reject/restore and missing-anchor cases.

  ```python
  def test_rejecting_summary_changes_only_summary_occurrence():
      baseline = "SUMMARY\nSQL analyst\nEXPERIENCE\n- Built SQL reports\n"
      change = ResumeChange(
          change_id="freeform:summary:0", section="summary", source_index=None,
          original_text="SUMMARY\nRetail analyst\n", proposed_text="SUMMARY\nSQL analyst\n",
          category=ChangeCategory.REPHRASED, reason="", job_requirement="",
          evidence_source="career_profile", evidence_text="Retail analyst",
          validation_status=ValidationStatus.PASS,
          disposition=ChangeDisposition.REJECTED,
          baseline_span=(0, len("SUMMARY\nSQL analyst\n")),
      )
      result = apply_dispositions_to_text(baseline, [change])
      assert result == "SUMMARY\nRetail analyst\nEXPERIENCE\n- Built SQL reports\n"
  ```

- [ ] **Step 2: Run the new test red**, then implement span validation (`baseline[start:end] == change.proposed_text`), descending-offset application, and a clear exception on mismatch or overlapping spans. Zero-length spans insert restored removed sections only at a validated section boundary. Leave the legacy loop intact for old reviews.

  ```python
  for change in sorted(span_changes, key=lambda item: item.baseline_span[0], reverse=True):
      start, end = change.baseline_span
      if text[start:end] != change.proposed_text:
          raise ValueError(f"Could not locate reviewed {change.section} text in this resume")
      text = text[:start] + final_text_for_change(change) + text[end:]
  ```

- [ ] **Step 3: Test a missing span, two overlapping section spans, repeated `SQL`, and the existing `legacy_review_format2.json` fixture.** Run `test_review_persistence.py`, `test_legacy_review_loads.py` and regeneration tests green.
- [ ] **Step 4: Commit this safe-regeneration increment** with the co-author trailer.

## Task 4: Guard AI/manual section edits and label them in both apps

**Files:** `artifacts/changes.py`, `artifacts/regeneration.py`, `tailoring_service.py`, `ui/tailor_progress.py`, `apps/api/app/workspace/tailor_router.py`, `apps/web/src/lib/types.ts`, `apps/web/src/app/tailor/review.tsx`, `pages/5_Tailor.py`; product/API/web tests from the file map.

**Interfaces:** `validate_manual_text(original_text, manual_text, profile, review=None)` keeps old callers valid; it appends `introduced_unsupported(original_text, manual_text, review)` to existing checks. `change_section_label(change) -> str` returns `Summary`, `Skills` or `Work experience`. `/v2/tailor` adds `section_label` to each change object without removing any field.

- [ ] **Step 1: Write failing guard tests** in product/API: a proposed summary adds an unsupported `CPA` or `4+ years`, and a manual skills edit adds `Snowflake` without confirmed evidence. Assert neither can yield a passing PDF/handoff.

  ```python
  def test_manual_summary_cannot_introduce_unsupported_credential():
      from tests.fixtures.ats import POSTING, PROVENANCE, profile
      analysis = JobAnalyzer().analyze(POSTING)
      candidate = profile()
      review = build_review(analysis, candidate, provenance=PROVENANCE, posting=POSTING)
      issues = validate_manual_text(
          "SUMMARY\nRetail analyst\n", "SUMMARY\nCPA retail analyst\n", candidate, review
      )
      assert any("CPA" in issue for issue in issues)
  ```

- [ ] **Step 2: Run guard tests red**, then reuse `introduced_unsupported` in section-change creation and manual validation; do not replace fabrication or semantic-drift checks. Pass the stored requirement review from `tailoring_service.regenerate` to manual validation. Convert a span mismatch to a plain `TailoringError`, never a silent 200 response.
- [ ] **Step 3: Add the shared section label** in `ui/tailor_progress.py` and expose it in the API change object. Render it in the Next.js queue/card and Streamlit change card. Add API and Playwright assertions that the new label appears while existing fields/choices remain.

  ```python
  def change_section_label(change: ResumeChange) -> str:
      return {"summary": "Summary", "skills": "Skills"}.get(change.section, "Work experience")
  ```

  ```tsx
  <span className="text-muted">{change.section_label}</span>
  ```

- [ ] **Step 4: Run focused product/API tests, web lint/types and all Playwright tests green.** Commit the guard/UI increment with the co-author trailer.

## Task 5: Supervised PDF run, complete verification and decision record

**Files:** `discovery/experiments/2026-10-spec-012-supervised-runs.md`, `decisions/034-complete-profile-sync-and-freeform-review.md`, spec 012 checkboxes/status.

- [ ] **Step 1: Run a real-model, synthetic PDF-upload tailoring session** with a supported summary rewrite and a wrapped skills line. Accept one section change and reject the other, reload the format-2 review and rebuild. Confirm the exact resulting text and readable PDF; record the prompt/model configuration without keys, all findings and the chosen decisions.
- [ ] **Step 2: Run complete product/API suites, web lint/types and Playwright** with the same Windows environment precautions as plan 012A. Confirm the existing 1,126/117/20 baseline has grown only through passing new tests; report any skipped or unavailable verification honestly.
- [ ] **Step 3: Finish decision 034 and the experiment record, update spec 012 only for verified outcomes, commit docs and push to `main`** after the plan is approved and tests are green. Check the five CI jobs. Keep the pre-existing `.claude/settings.local.json` out of every commit.

## Plan self-check

- Spec 012B coverage: section identification, separate choices, unsupported-term checks, manual validation, safe regeneration, both UIs, legacy compatibility and the supervised run map to Tasks 1–5.
- No change to the global greedy matcher or employer submission behavior is proposed.
