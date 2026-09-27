# Steps 16-20 Validated Artifact Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn approved tailoring output into traceable DOCX/PDF artifacts that preserve the source design, fail closed on document defects, explain every meaningful change, and support user review.

**Architecture:** Add a shared artifact package under `product/resume_tailorer/` and make both FastAPI and Streamlit call it. Keep the existing DOCX splice and PDF reconstruction engines, wrap them with shared change, validation, report, and pipeline models, then persist immutable runs/artifacts in the API.

**Tech Stack:** Python 3.11+, dataclasses/enums, python-docx, docx2pdf, ReportLab, pypdf, PyMuPDF 1.24+, SQLAlchemy, FastAPI, Streamlit, pytest.

**Spec:** `specs/002-steps-16-20-validated-artifact-pipeline.md`

## Global Constraints

- `product/resume_tailorer/` is the source of truth; API and Streamlit remain adapters.
- DOCX generation may replace text in existing paragraphs but may not add, remove, or reorder paragraphs.
- PDF-only fidelity is reported as `RECONSTRUCTED`; DOCX fidelity is `PRESERVED` only after validation.
- The Career Truth Profile is the only source of candidate facts.
- Candidate Fit is immutable across tailoring and separate from Resume Alignment.
- The correction loop runs at most once and may only condense verified content; it never shrinks fonts or margins.
- Existing `/tailor/preview` response fields remain backward compatible through additive fields.
- No real names, emails, phone numbers, or unredacted resumes enter fixtures or commits.
- Baseline before implementation: product 548 passed; API 39 passed.

## Review Focus

- A DOCX bullet with mixed inline formatting must warn without changing non-target paragraph/run XML; covered in Task 2.
- A visual validator must tolerate antialiasing while catching content movement outside edited regions; covered in Task 3.
- A validation retry must never run twice or retry truth/conversion failures; covered in Task 4.
- Concurrent or repeated review requests must create immutable artifact versions without overwriting prior bytes; covered in Task 6.
- A rejected or manually edited change must be reflected in the exact regenerated artifact and report; covered in Task 7.

---

### Task 1: Shared artifact domain and safe filenames

**Files:**
- Create: `product/resume_tailorer/artifacts/__init__.py`
- Create: `product/resume_tailorer/artifacts/models.py`
- Create: `product/resume_tailorer/artifacts/filenames.py`
- Create: `product/tests/test_artifact_models.py`
- Create: `product/tests/test_artifact_filenames.py`

**Interfaces:**
- Produces: `ValidationStatus`, `FindingSeverity`, `FindingCategory`, `ValidationFinding`, `ArtifactValidation`, `FidelityMode`, `ChangeCategory`, `ChangeDisposition`, `ResumeChange`, `ArtifactMetadata`, `FinalApplicationReport`, and `safe_artifact_filename(company, role, version, extension)`.
- Consumes: standard-library dataclasses, enums, hashing, and JSON-compatible values only.

- [ ] **Step 1: Write failing model and filename tests**

```python
def test_validation_status_is_derived_from_findings():
    warning = ValidationFinding("VISUAL_CHECK_SKIPPED", FindingSeverity.WARNING,
                                FindingCategory.VISUAL, "Visual check unavailable")
    assert ArtifactValidation.from_findings([warning]).status is ValidationStatus.WARNING

def test_fail_takes_precedence_over_warning():
    findings = [
        ValidationFinding("LINK_LOST", FindingSeverity.WARNING, FindingCategory.ATS, "Link lost"),
        ValidationFinding("PAGE_COUNT_CHANGED", FindingSeverity.FAIL, FindingCategory.VISUAL,
                          "Page count changed"),
    ]
    assert ArtifactValidation.from_findings(findings).status is ValidationStatus.FAIL

def test_safe_filename_is_deterministic_and_sanitized():
    assert safe_artifact_filename("ACME / Labs", "Strategy: Lead", 2, "pdf") == (
        "ACME_Labs_Strategy_Lead_Tailored_Resume_v2.pdf"
    )
```

- [ ] **Step 2: Run the new tests and verify import failures**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_artifact_models.py tests/test_artifact_filenames.py -q --basetemp=.codex-pytest-task1 -p no:cacheprovider`

Expected: FAIL because `resume_tailorer.artifacts` does not exist.

- [ ] **Step 3: Implement immutable shared models and filename sanitization**

Use string-valued enums. Make `ResumeChange` contain `change_id`, `section`, `source_index`, `original_text`, `proposed_text`, `category`, `reason`, `job_requirement`, `evidence_source`, `evidence_text`, `validation_status`, and `disposition`. Implement `ArtifactValidation.from_findings()` with `FAIL > WARNING > PASS` precedence. Sanitize filename components with `re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")` and fall back to `Target`/`Job`.

- [ ] **Step 4: Run focused and existing model tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_artifact_models.py tests/test_artifact_filenames.py tests/test_application_models.py -q --basetemp=.codex-pytest-task1 -p no:cacheprovider`

Expected: PASS.

- [ ] **Step 5: Commit the domain boundary**

```bash
git add product/resume_tailorer/artifacts product/tests/test_artifact_models.py product/tests/test_artifact_filenames.py
git commit -m "feat: add validated artifact domain models"
```

### Task 2: DOCX layout signatures and authoritative change records

**Files:**
- Create: `product/resume_tailorer/docx_export/layout_signature.py`
- Create: `product/tests/test_docx_layout_signature.py`
- Modify: `product/resume_tailorer/tailorer/docx_bullet_tailorer.py`
- Modify: `product/resume_tailorer/docx_export/splicer.py`
- Modify: `product/resume_tailorer/docx_export/pipeline.py`
- Modify: `product/tests/test_docx_splicer.py`
- Modify: `product/tests/test_docx_pipeline.py`

**Interfaces:**
- Consumes: Task 1 `ResumeChange`, `ArtifactValidation`, and validation enums; existing `BulletEdit`.
- Produces: `capture_layout_signature(doc) -> DocxLayoutSignature`, `compare_layout_signatures(before, after) -> list[ValidationFinding]`, and `changes_from_bullet_edits(edits, bullets, gap_report) -> list[ResumeChange]`.

- [ ] **Step 1: Write failing signature, mixed-format, and authoritative-change tests**

```python
def test_text_replacement_preserves_immutable_layout_signature(sample_doc):
    before = capture_layout_signature(sample_doc)
    splice_bullets_into_docx(sample_doc, [BulletEdit(3, "Old", "New", True)])
    after = capture_layout_signature(sample_doc)
    assert compare_layout_signatures(before, after) == []

def test_paragraph_reorder_is_a_failure(sample_doc):
    before = capture_layout_signature(sample_doc)
    sample_doc._body._body.insert(0, sample_doc.paragraphs[-1]._p)
    findings = compare_layout_signatures(before, capture_layout_signature(sample_doc))
    assert any(f.code == "DOCX_PARAGRAPH_ORDER_CHANGED" for f in findings)

def test_mixed_inline_formatting_on_changed_bullet_warns():
    doc = Document()
    paragraph = doc.add_paragraph(style="List Paragraph")
    paragraph.add_run("Led ")
    paragraph.add_run("critical").bold = True
    paragraph.add_run(" launch")
    findings = inline_formatting_findings(paragraph, changed=True)
    assert [finding.code for finding in findings] == ["INLINE_FORMATTING_SIMPLIFIED"]

def test_docx_result_uses_bullet_edit_pairing_not_similarity_matching():
    bullet = Bullet(7, "Original exact bullet", "work_experience", job_index=0)
    edit = BulletEdit(7, "Original exact bullet", "Tailored exact bullet", True)
    changes = changes_from_bullet_edits(
        [edit], [bullet], GapReport(items=[], summary="No gaps")
    )
    assert changes[0].source_index == 7
    assert changes[0].original_text == "Original exact bullet"
```

- [ ] **Step 2: Run the focused tests and verify failures**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_docx_layout_signature.py tests/test_docx_splicer.py tests/test_docx_pipeline.py -q --basetemp=.codex-pytest-task2 -p no:cacheprovider`

Expected: FAIL on missing signature and change-record APIs.

- [ ] **Step 3: Implement XML-derived immutable signatures**

Capture section page size/margins/header/footer relationship IDs plus, for every paragraph, its index, style ID, numbering XML, indentation, tabs, spacing, borders, and an identity hash of non-editable text. Exclude target paragraph text from equality but never exclude its paragraph/style properties.

- [ ] **Step 4: Emit mixed-run warnings and authoritative changes**

Before collapsing runs, detect differing `(bold, italic, underline, font name, font size)` tuples. Add `INLINE_FORMATTING_SIMPLIFIED` as a warning. Extend `DocxTailoringResult` with `changes` and structured `validation`; derive the change ID from run ID + paragraph index and attach the best matching Gap Report requirement/evidence without asking the LLM.

- [ ] **Step 5: Run DOCX tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_docx_structure.py tests/test_docx_splicer.py tests/test_docx_layout_signature.py tests/test_docx_pipeline.py tests/test_docx_bullet_tailorer.py -q --basetemp=.codex-pytest-task2 -p no:cacheprovider`

Expected: PASS.

- [ ] **Step 6: Commit DOCX fidelity validation**

```bash
git add product/resume_tailorer/docx_export product/resume_tailorer/tailorer/docx_bullet_tailorer.py product/tests/test_docx_*.py
git commit -m "feat: validate DOCX layout preservation"
```

### Task 3: Structured PDF/content/visual validation

**Files:**
- Modify: `product/requirements.txt`
- Modify: `apps/api/pyproject.toml`
- Create: `product/resume_tailorer/pdf/visual_validator.py`
- Create: `product/resume_tailorer/pdf/content_validator.py`
- Modify: `product/resume_tailorer/pdf/validator.py`
- Create: `product/tests/test_pdf_content_validator.py`
- Create: `product/tests/test_pdf_visual_validator.py`
- Modify: `product/tests/test_pdf_validator.py`

**Interfaces:**
- Consumes: Task 1 validation models, original/tailored PDFs, Career Truth Profile, accepted changes, and expected page count.
- Produces: `PDFValidator.validate_artifact(pdf_path, profile, expected_page_count, accepted_changes, original_pdf_path=None) -> ArtifactValidation`, while retaining legacy `validate(path, target_length) -> ValidationResult`.

- [ ] **Step 1: Add PyMuPDF dependency**

Add `PyMuPDF>=1.24.0,<2.0.0` to both dependency files. Install into both existing venvs before running the new tests.

- [ ] **Step 2: Write failing structural/content/visual tests**

```python
def test_missing_contact_is_fail(generated_pdf, profile):
    result = PDFValidator().validate_artifact(generated_pdf, profile=profile,
                                              expected_page_count=1, accepted_changes=[])
    assert result.has_code("CONTACT_MISSING")
    assert result.status is ValidationStatus.FAIL

def test_visual_change_outside_edited_region_fails(original_pdf, shifted_header_pdf):
    result = compare_pdf_renders(original_pdf, shifted_header_pdf, edited_regions=[])
    assert any(f.code == "LAYOUT_DRIFT_OUTSIDE_EDIT" for f in result)

def test_antialiasing_noise_inside_edited_region_passes(original_pdf, tailored_pdf):
    assert not any(f.severity is FindingSeverity.FAIL for f in
                   compare_pdf_renders(original_pdf, tailored_pdf, edited_regions=[EDIT_BOX]))
```

- [ ] **Step 3: Run focused tests and verify failures**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_pdf_validator.py tests/test_pdf_content_validator.py tests/test_pdf_visual_validator.py -q --basetemp=.codex-pytest-task3 -p no:cacheprovider`

Expected: FAIL on missing validators.

- [ ] **Step 4: Implement deterministic content validation**

Normalize Unicode/whitespace, then verify contact identifiers, employers, dates, education, metrics, accepted bullets, duplicates, common unfinished-marker strings, bracketed fill-ins, and commentary patterns. Use stable finding codes; never compare only raw byte strings.

- [ ] **Step 5: Implement render-based geometry validation**

Use PyMuPDF to render pages and read text blocks. Fail on page-dimension/page-count drift, block intersections, blocks outside page bounds, or changed pixels/text blocks outside padded edited regions. Use a 3-pixel region padding and ignore isolated pixel differences smaller than 0.25% of page pixels; fixtures pin these thresholds.

- [ ] **Step 6: Preserve the legacy validator adapter and run tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_pdf_generator.py tests/test_pdf_validator.py tests/test_pdf_content_validator.py tests/test_pdf_visual_validator.py -q --basetemp=.codex-pytest-task3 -p no:cacheprovider`

Expected: PASS, including all pre-existing `ValidationResult` tests.

- [ ] **Step 7: Commit validation gate**

```bash
git add product/requirements.txt apps/api/pyproject.toml product/resume_tailorer/pdf product/tests/test_pdf_*.py
git commit -m "feat: add structured visual PDF validation"
```

### Task 4: Shared artifact orchestration and bounded correction

**Files:**
- Create: `product/resume_tailorer/artifacts/pipeline.py`
- Create: `product/tests/test_artifact_pipeline.py`
- Modify: `product/resume_tailorer/docx_export/pipeline.py`
- Modify: `product/resume_tailorer/pdf/generator.py`
- Modify: `product/resume_tailorer/tailorer/resume_tailorer.py`

**Interfaces:**
- Consumes: Tasks 1-3, original bytes/name, profile, job analysis/snapshot, gap report, fit breakdown, and injected tailoring/correction collaborators.
- Produces: `ValidatedArtifactPipeline.run(request: ArtifactPipelineRequest) -> ArtifactPipelineResult`.

- [ ] **Step 1: Write failing dispatch and retry tests**

```python
def test_docx_dispatch_uses_master_template(docx_request, docx_runner):
    result = ValidatedArtifactPipeline(docx_runner=docx_runner).run(docx_request)
    docx_runner.assert_called_once()
    assert result.fidelity_mode is FidelityMode.PRESERVED

def test_overflow_gets_exactly_one_correction(pdf_request, corrector):
    result = pipeline_with_validation_sequence("PAGE_COUNT_CHANGED", "PASS").run(pdf_request)
    assert corrector.call_count == 1
    assert result.attempt_count == 2

def test_truth_failure_is_never_retried(pdf_request, corrector):
    result = pipeline_with_validation_sequence("UNSUPPORTED_CLAIM").run(pdf_request)
    assert corrector.call_count == 0
    assert result.validation.status is ValidationStatus.FAIL
```

- [ ] **Step 2: Run the new tests and verify failures**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_artifact_pipeline.py -q --basetemp=.codex-pytest-task4 -p no:cacheprovider`

Expected: FAIL because the orchestrator does not exist.

- [ ] **Step 3: Implement one dispatch path and fail-closed downloads**

Define `ArtifactPipelineRequest` with immutable snapshots and `ArtifactPipelineResult` with artifacts, changes, validation, scoring text, fidelity mode, and attempt count. Dispatch by original extension. Expose `application_ready = validation.status is PASS`; keep warning artifacts reviewable but not silently ready.

- [ ] **Step 4: Implement the one-retry correction policy**

Retry only when every failure code is in `{PAGE_COUNT_CHANGED, TEXT_OVERFLOW, CLIPPED_TEXT}`. Pass exact findings and editable change IDs to the correction collaborator, rerun truth checks, then regenerate from untouched original bytes. Record both attempts; return the second result even when failed.

- [ ] **Step 5: Run orchestration and existing pipeline tests**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_artifact_pipeline.py tests/test_docx_pipeline.py tests/test_resume_tailorer.py tests/test_pdf_generator.py -q --basetemp=.codex-pytest-task4 -p no:cacheprovider`

Expected: PASS.

- [ ] **Step 6: Commit orchestration**

```bash
git add product/resume_tailorer/artifacts/pipeline.py product/resume_tailorer/docx_export/pipeline.py product/resume_tailorer/pdf/generator.py product/resume_tailorer/tailorer/resume_tailorer.py product/tests/test_artifact_pipeline.py
git commit -m "feat: orchestrate validated resume artifacts"
```

### Task 5: One final report and evidence-backed change set

**Files:**
- Create: `product/resume_tailorer/artifacts/report.py`
- Create: `product/resume_tailorer/artifacts/changes.py`
- Modify: `product/resume_tailorer/report_generator.py`
- Modify: `product/resume_tailorer/diff_generator.py`
- Modify: `product/tests/test_report_generator.py`
- Modify: `product/tests/test_resume_diff.py`
- Create: `product/tests/test_artifact_report.py`

**Interfaces:**
- Consumes: existing cf-v2 breakdown, benchmark/optimizer scores, Gap Report, authoritative DOCX changes or freeform diff candidates, and artifact validation.
- Produces: `build_final_report(candidate_fit, fit_breakdown, original_alignment, tailored_alignment, gap_report, validation, artifacts) -> FinalApplicationReport` and `build_freeform_changes(profile, tailored_text, gap_report) -> list[ResumeChange]`.

- [ ] **Step 1: Write failing report invariance and evidence tests**

```python
def test_candidate_fit_is_copied_not_recomputed(inputs):
    report = build_final_report(candidate_fit=inputs.fit, original_alignment=.56,
                                tailored_alignment=.60, **inputs.rest)
    assert report.candidate_fit == inputs.fit["score"]
    assert report.fit_breakdown["scoring_version"] == "cf-v2"

def test_change_includes_requirement_evidence_and_safety(change_inputs):
    change = build_freeform_changes(**change_inputs)[0]
    assert change.job_requirement
    assert change.evidence_text
    assert change.validation_status in ValidationStatus
```

- [ ] **Step 2: Run report/diff tests and verify failures**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_artifact_report.py tests/test_report_generator.py tests/test_resume_diff.py -q --basetemp=.codex-pytest-task5 -p no:cacheprovider`

Expected: FAIL on missing shared builders.

- [ ] **Step 3: Implement report mapping without new scoring**

Copy cf-v2 eligibility/core/preferred/evidence values when present; use `NOT_ASSESSED` only for `None`. Populate strong/partial/true-gap lists from the scorer and Gap Report. Preserve existing report keys through `ReportGenerator` as a compatibility adapter over `FinalApplicationReport`.

- [ ] **Step 4: Enrich freeform diffs and retain ambiguity**

Add a minimum similarity threshold of 0.45. Pairings below it become `REJECTED`/review-required rather than confident modifications. Attach Gap Report evidence deterministically; do not generate reasons with the LLM.

- [ ] **Step 5: Run tests and commit**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_artifact_report.py tests/test_report_generator.py tests/test_resume_diff.py -q --basetemp=.codex-pytest-task5 -p no:cacheprovider`

Expected: PASS.

```bash
git add product/resume_tailorer/artifacts product/resume_tailorer/report_generator.py product/resume_tailorer/diff_generator.py product/tests/test_artifact_report.py product/tests/test_report_generator.py product/tests/test_resume_diff.py
git commit -m "feat: unify tailoring report and change evidence"
```

### Task 6: Persist immutable runs and artifact versions

**Files:**
- Modify: `apps/api/app/models.py`
- Modify: `apps/api/app/migrations.py`
- Create: `apps/api/app/tailor/storage.py`
- Create: `apps/api/app/schemas/artifact.py`
- Create: `apps/api/tests/test_tailoring_artifact_storage.py`
- Create: `apps/api/tests/test_tailoring_artifact_migrations.py`

**Interfaces:**
- Consumes: serialized Task 1/4/5 results.
- Produces: SQLAlchemy `TailoringRun` and `TailoredArtifact`; `TailoringRunStore.create_run`, `save_artifact`, `get_owned_run`, `get_owned_artifact`, and `next_artifact_version`.

- [ ] **Step 1: Write failing persistence and ownership tests**

```python
def test_regeneration_creates_new_immutable_version(db, user, stored_run):
    first = store.save_artifact(stored_run.id, "PDF", b"one", "one.pdf", "PASS")
    second = store.save_artifact(stored_run.id, "PDF", b"two", "two.pdf", "PASS")
    assert (first.version, second.version) == (1, 2)
    assert db.get(TailoredArtifact, first.id).data == b"one"

def test_user_cannot_read_another_users_artifact(client, two_users, artifact):
    response = client.get(f"/tailor/artifacts/{artifact.id}", headers=two_users.other_headers)
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests and verify missing models**

Run: `cd apps\api; .\.venv\Scripts\python.exe -m pytest tests/test_tailoring_artifact_storage.py tests/test_tailoring_artifact_migrations.py -q --basetemp=.codex-pytest-task6 -p no:cacheprovider`

Expected: FAIL because persistence types do not exist.

- [ ] **Step 3: Implement additive tables and storage service**

Create tables rather than modifying existing resume tables. Store snapshot/change/report/validation JSON as canonical JSON, binary bytes plus SHA-256/size, and a uniqueness constraint on `(run_id, kind, version)`. Store profile snapshot hash and original resume ID/version. All reads include `user_id` ownership.

- [ ] **Step 4: Run API persistence tests**

Run: `cd apps\api; .\.venv\Scripts\python.exe -m pytest tests/test_tailoring_artifact_storage.py tests/test_tailoring_artifact_migrations.py tests/test_profile_api.py -q --basetemp=.codex-pytest-task6 -p no:cacheprovider`

Expected: PASS.

- [ ] **Step 5: Commit persistence**

```bash
git add apps/api/app/models.py apps/api/app/migrations.py apps/api/app/tailor/storage.py apps/api/app/schemas/artifact.py apps/api/tests/test_tailoring_artifact_storage.py apps/api/tests/test_tailoring_artifact_migrations.py
git commit -m "feat: persist immutable tailoring artifacts"
```

### Task 7: API preview, review, regenerate, and download flow

**Files:**
- Modify: `apps/api/app/tailor/router.py`
- Modify: `apps/api/app/schemas/tailor.py`
- Modify: `apps/api/tests/test_tailor_router.py`
- Create: `apps/api/tests/test_tailor_review.py`

**Interfaces:**
- Consumes: shared pipeline/report/change models and Task 6 storage.
- Produces: additive preview fields plus `GET /tailor/runs/{run_id}`, `PATCH /tailor/runs/{run_id}/changes`, `POST /tailor/runs/{run_id}/regenerate`, and `GET /tailor/artifacts/{artifact_id}`.

- [ ] **Step 1: Write failing end-to-end review tests**

```python
def test_preview_persists_run_and_keeps_legacy_fields(client, prepared_user):
    data = client.post("/tailor/preview", json=prepared_user.request,
                       headers=prepared_user.headers).json()
    assert data["tailored_resume"]
    assert data["run_id"]
    assert data["validation"]["status"] in {"PASS", "WARNING", "FAIL"}

def test_reject_then_regenerate_restores_original(client, proposed_run):
    client.patch(f"/tailor/runs/{proposed_run.id}/changes", headers=proposed_run.headers,
                 json={"changes": [{"change_id": proposed_run.change_id,
                                     "disposition": "REJECTED"}]})
    result = client.post(f"/tailor/runs/{proposed_run.id}/regenerate",
                         headers=proposed_run.headers).json()
    assert proposed_run.proposed_text not in decode_artifact(result)
    assert proposed_run.original_text in decode_artifact(result)
```

- [ ] **Step 2: Run focused tests and verify route failures**

Run: `cd apps\api; .\.venv\Scripts\python.exe -m pytest tests/test_tailor_router.py tests/test_tailor_review.py -q --basetemp=.codex-pytest-task7 -p no:cacheprovider`

Expected: FAIL on missing additive fields/routes.

- [ ] **Step 3: Route preview through the shared pipeline**

Preserve all old response fields, add run/report/validation/change/artifact metadata, persist the run, and return base64 fields during compatibility migration. Store the original request snapshots needed for deterministic regeneration.

- [ ] **Step 4: Implement review validation and regeneration**

Reject unknown/duplicate change IDs. Validate manual text with the shared truth/semantic/length checks before saving it. Apply dispositions to the original change set, regenerate from original bytes, save new immutable artifacts, and return the latest report/validation.

- [ ] **Step 5: Implement owned downloads and fail-closed labels**

Return exact bytes, MIME type, content disposition, checksum ETag, and validation headers. A failed artifact remains retrievable only through the diagnostic run response, not the application-ready download endpoint.

- [ ] **Step 6: Run API tests and commit**

Run: `cd apps\api; .\.venv\Scripts\python.exe -m pytest -q --basetemp=.codex-pytest-task7 -p no:cacheprovider`

Expected: all API tests pass.

```bash
git add apps/api/app/tailor apps/api/app/schemas/tailor.py apps/api/tests/test_tailor_router.py apps/api/tests/test_tailor_review.py
git commit -m "feat: add tailoring review and regeneration API"
```

### Task 8: Migrate Streamlit to the shared pipeline and add review controls

**Files:**
- Modify: `product/resume_tailorer/app.py`
- Create: `product/resume_tailorer/ui/artifact_review.py`
- Create: `product/tests/test_artifact_review_ui.py`
- Modify: `product/tests/test_integration.py`

**Interfaces:**
- Consumes: `ArtifactPipelineResult`, `FinalApplicationReport`, and `ResumeChange`.
- Produces: pure rendering/state helpers plus Streamlit orchestration that uses shared DOCX/PDF dispatch.

- [ ] **Step 1: Write failing UI-state tests**

```python
def test_default_view_hides_unchanged_and_punctuation_only_changes():
    assert visible_changes(CHANGES, advanced=False) == [MEANINGFUL_CHANGE]

def test_rejected_and_manual_edits_build_expected_review_payload():
    payload = build_review_payload({"c1": "REJECTED", "c2": "MANUALLY_EDITED"},
                                   {"c2": "User-approved text"})
    assert payload["changes"][1]["manual_text"] == "User-approved text"
```

- [ ] **Step 2: Run tests and verify missing helpers**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest tests/test_artifact_review_ui.py tests/test_integration.py -q --basetemp=.codex-pytest-task8 -p no:cacheprovider`

Expected: FAIL on missing UI module.

- [ ] **Step 3: Build testable review helpers and migrate orchestration**

Keep data shaping outside Streamlit calls. Replace direct `ResumeTailorer -> PDFGenerator -> PDFValidator -> ReportGenerator` orchestration with `ValidatedArtifactPipeline`. Preserve pending job handoff and LLM settings. Ensure a DOCX upload reaches the DOCX splice path.

- [ ] **Step 4: Add concise report, change controls, diagnostics, and downloads**

Show Candidate Fit separately from alignment; show meaningful changes by default; add advanced diff; expose accept/reject/restore/manual edit; regenerate on review submission; offer application-ready downloads only for `PASS`, explicit-warning downloads for `WARNING`, and none for `FAIL`.

- [ ] **Step 5: Run product tests and commit**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest -q --basetemp=.codex-pytest-task8 -p no:cacheprovider`

Expected: all product tests pass.

```bash
git add product/resume_tailorer/app.py product/resume_tailorer/ui/artifact_review.py product/tests/test_artifact_review_ui.py product/tests/test_integration.py
git commit -m "feat: add validated resume review workflow"
```

### Task 9: Real-world acceptance, documentation, and final verification

**Files:**
- Create: `product/tests/fixtures/artifacts/README.md`
- Create: anonymized fixture files under `product/tests/fixtures/artifacts/`
- Create: `product/tests/test_artifact_acceptance.py`
- Modify: `HANDOFF-TO-CODEX.md`
- Modify: `AGENTS.md`
- Create: `decisions/015-steps-16-20-build-summary.md`

**Interfaces:**
- Consumes: the completed pipeline through public APIs only.
- Produces: acceptance evidence, current-state documentation, and an honest limitation record.

- [ ] **Step 1: Add anonymized acceptance fixtures and provenance README**

Create one DOCX and one PDF-only resume with fictitious names/contact data plus a real public job description snapshot with employer identifiers removed when necessary. Document what each fixture is intended to exercise.

- [ ] **Step 2: Write acceptance tests**

Assert same DOCX page count and immutable signature, all jobs/education/contact/metrics present, no unsupported claims, correct report separation, accurate diffs, rejection/manual-edit regeneration, PDF-only `RECONSTRUCTED` labeling, and immutable artifact lineage.

- [ ] **Step 3: Run both full suites from writable basetemps**

Run: `cd product; .\.venv\Scripts\python.exe -m pytest -q --basetemp=.codex-pytest-final -p no:cacheprovider`

Expected: all product tests pass.

Run: `cd apps\api; .\.venv\Scripts\python.exe -m pytest -q --basetemp=.codex-pytest-final -p no:cacheprovider`

Expected: all API tests pass.

- [ ] **Step 4: Run one live anonymized DOCX and PDF workflow**

Use the configured LLM only if local keys are present. Inspect rendered pages and extracted text. Record exact pass/warning/failure results; do not commit the user's real resume or job application data.

- [ ] **Step 5: Update handoff and decision summary**

Record final test counts, live verification results, known limitations, migration notes, and any acceptance item that remains unavailable because Word or LLM credentials were not present.

- [ ] **Step 6: Commit acceptance and documentation**

```bash
git add product/tests/fixtures/artifacts product/tests/test_artifact_acceptance.py HANDOFF-TO-CODEX.md AGENTS.md decisions/015-steps-16-20-build-summary.md
git commit -m "docs: close Steps 16-20 validated artifact build"
```

## Execution decision

Use **Native execution** in the current session. The tasks share evolving interfaces and database/API compatibility constraints, so keeping implementation in one context is faster and less error-prone than dispatching independent agents. Request one whole-branch review after Task 9, then fix findings and rerun both full suites before claiming completion.
