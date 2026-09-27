# Steps 16-20: Validated Resume Artifact Pipeline

**Status:** Proposed
**Date:** 2026-09-27
**Owner:** Product and engineering

## 1. Purpose

Steps 16-20 turn approved tailored content into a resume the job seeker can safely review and
submit. The system must preserve the original document, generate editable and PDF artifacts,
reject broken output, explain every meaningful change, and keep Candidate Fit separate from
resume alignment.

The user outcome is simple: a job seeker receives a tailored resume that still looks like their
resume, contains only verified facts, and is transparent about what changed.

## 2. Scope

This specification covers:

1. Step 16: preserve the original resume design.
2. Step 17: generate deterministic DOCX/PDF artifacts.
3. Step 18: validate structure, content, truthfulness, rendering, and page count.
4. Step 19: produce one consistent final application report.
5. Step 20: show evidence-backed changes and let the user accept, reject, restore, or edit them.
6. Persist tailoring runs and generated artifact versions without overwriting the master resume.
7. Use the same shared product-engine workflow from Streamlit and FastAPI.

This specification does not cover browser-based job submission, ATS form automation, new job
sources, or redesigning Steps 1-15.

## 3. Existing architecture that must be preserved

- `product/resume_tailorer/` remains the shared source of truth. The API delegates to it.
- DOCX originals use the original DOCX as the master template. Text is replaced in existing
  paragraphs; paragraphs are never added, removed, or reordered.
- PDF-only originals use controlled application-owned reconstruction because the source has no
  editable document structure.
- The Career Truth Profile remains the only source of candidate facts.
- Existing semantic-drift and fabrication checks remain hard safety gates.
- Candidate Fit measures background-to-job fit. Resume Alignment measures how well a particular
  resume version communicates that background. Tailoring may change only Resume Alignment.

## 4. Architectural decision

Build one shared validated-artifact pipeline in `product/resume_tailorer/`. Streamlit and
FastAPI become adapters that collect inputs, call the shared pipeline, persist or display its
result, and never reimplement document generation, validation, reporting, or diff logic.

The pipeline consumes:

- original resume bytes and filename;
- original resume version identifier;
- Career Truth Profile plus its version or immutable snapshot;
- job snapshot and structured Job Requirement model;
- Gap Report and Candidate Fit result;
- approved tailoring output from Steps 10-15;
- authoritative DOCX `BulletEdit` records when the source is DOCX.

It produces:

- a proposed change set;
- a tailored editable artifact when possible;
- a tailored PDF when conversion/rendering is available;
- structured validation findings and an overall status;
- a final application report;
- immutable metadata connecting every output to its inputs.

## 5. Domain model

### 5.1 Validation status and findings

Use an enum with exactly:

- `PASS`: no blocking or warning findings.
- `WARNING`: usable output with a disclosed non-blocking limitation.
- `FAIL`: output must not be offered as application-ready.

Each validation finding contains:

- `code`: stable machine-readable identifier;
- `severity`: `WARNING` or `FAIL`;
- `category`: `STRUCTURE`, `CONTENT`, `TRUTH`, `VISUAL`, `ATS`, or `CONVERSION`;
- `message`: concise user-facing explanation;
- `details`: structured diagnostic values where useful.

The aggregate result contains status, findings, original/tailored page counts, extracted text,
and the checks that ran. A skipped visual check is a `WARNING`, never an implied pass.

### 5.2 Change record

Each meaningful proposed change contains:

- stable `change_id` within a tailoring run;
- section and source paragraph/bullet identity;
- original and proposed text;
- category: `REPHRASED`, `REORDERED`, `CONDENSED`, `COMPETENCY_CHANGED`, `UNCHANGED`, or
  `REJECTED`;
- reason;
- supported job requirement;
- evidence source and evidence text;
- safety/validation status;
- user disposition: `PENDING`, `ACCEPTED`, `REJECTED`, `RESTORED`, or `MANUALLY_EDITED`.

Punctuation-only changes are retained in the full audit data but hidden from the default UI.

### 5.3 Tailoring run and artifacts

Persist one `TailoringRun` per preview/review lifecycle with:

- user ID and tailoring run ID;
- original resume stable ID and version;
- Career Truth Profile version or immutable JSON snapshot hash;
- immutable job snapshot;
- request options and timestamps;
- Candidate Fit result and original/tailored alignment results;
- proposed and reviewed change sets;
- validation result;
- run state: `PROPOSED`, `REVIEWED`, `VALIDATED`, or `FAILED`.

Persist each output as a versioned `TailoredArtifact` with:

- artifact ID, run ID, version, kind (`DOCX` or `PDF`), safe filename, MIME type, bytes,
  checksum, size, and creation timestamp;
- validation status for the exact bytes stored;
- superseded artifact ID when regeneration creates a new version.

Artifacts are immutable. Regeneration creates a new version. The master resume is never
overwritten.

## 6. Step 16: preserve design

### 6.1 DOCX source

The existing splice pipeline remains canonical. It must:

- mutate text only in approved target paragraphs;
- preserve section properties, margins, page dimensions, headers, footers, borders, tabs,
  numbering, paragraph styles, and paragraph order;
- preserve the first run's formatting for rewritten text;
- detect a rewritten paragraph containing meaningful mixed inline formatting and emit a
  `WARNING` when exact word-level formatting cannot be retained;
- capture a pre/post layout signature for immutable structure.

The layout signature includes section count/order, paragraph count/order, style IDs, numbering
properties, indentation, tab stops, paragraph spacing, line spacing, borders, page dimensions,
margins, header/footer relationships, and contact/header paragraph text.

Any unexpected immutable-structure difference is a `FAIL`.

### 6.2 PDF-only source

PDF-only output remains a controlled reconstruction. The application extracts and reuses page
count, page dimensions, dominant font family category, approximate font sizes, margins,
section-heading treatment, bullet symbol/indentation, and spacing where reliably detectable.

The UI and report must label fidelity as `RECONSTRUCTED`, not `PRESERVED`. Failure to recover a
style attribute uses a documented ATS-safe default and emits a warning only when the fallback
materially changes the result.

The LLM never emits layout instructions or document markup.

## 7. Step 17: generate artifacts

### 7.1 DOCX path

1. Apply only accepted or pending-preview text replacements to a fresh copy of the original
   DOCX bytes.
2. Save a new DOCX artifact.
3. Convert that exact DOCX to PDF through the existing bounded Word/docx2pdf converter.
4. Never alter font sizes or margins to force content to fit.

### 7.2 PDF-only path

Generate a searchable PDF through the controlled ReportLab template layer. The template may
adapt content but may not silently remove jobs, education, contact data, metrics, or bullets.

### 7.3 Filenames

Use sanitized deterministic base names:

`{Company}_{Role}_Tailored_Resume_v{artifact_version}.{extension}`

Replace unsafe characters with underscores, collapse repeats, strip leading/trailing separators,
and fall back to `Target_Job` for missing company/role data.

## 8. Step 18: validation and correction loop

### 8.1 Structural checks

Fail when:

- the file is absent, empty, corrupt, or cannot be opened;
- no text can be extracted from the PDF;
- page count exceeds the original target;
- expected contact identity, employers, job dates, education entries, or section order is lost;
- DOCX immutable structure changes unexpectedly;
- bullet count changes without an explicit reviewed change authorizing it.

### 8.2 Content and truth checks

Fail when:

- an original metric, employer, date, location, or accepted bullet is missing;
- unsupported claims or fabrication-risk findings exist;
- LLM commentary, prompt text, placeholder text, or duplicated bullets appear;
- a bullet appears truncated;
- a rejected/restored change appears in the generated artifact.

### 8.3 ATS checks

Fail when text is not selectable/extractable or reading order loses required sections. Emit a
warning for suspicious symbol replacement or links that are visible but not retained as links.

### 8.4 Visual checks

Add PyMuPDF as the PDF rendering dependency. Render original and tailored PDFs at the same
resolution. Analyze page dimensions, occupied content bounds, unexpected blank regions,
out-of-page content, text-block overlap, and layout-wide image differences.

Expected visual differences must cluster around paragraphs represented by accepted change
records. Large differences outside those regions fail. Small antialiasing or line-wrap changes
inside an edited region do not fail by themselves.

The first implementation uses deterministic geometric thresholds covered by fixtures; it does
not use an LLM or subjective vision model for validation.

### 8.5 Bounded correction loop

Run at most one automatic correction after the initial artifact fails for correctable length or
overflow reasons:

1. return the exact validation findings to the content-correction component;
2. request condensation only within already-approved claims and affected editable paragraphs;
3. rerun semantic-drift, fabrication, and metric-preservation checks;
4. regenerate and revalidate from the untouched original template.

Do not retry corruption, missing-identity, unsupported-claim, conversion-unavailable, or
immutable-layout failures automatically. If the second validation fails, persist the failed run,
explain why, and withhold an application-ready download.

## 9. Step 19: final application report

Create one shared report model and generator used by Streamlit and FastAPI. It contains:

- company and role;
- Candidate Fit, sourced from the existing shared scorer;
- Eligibility Match, Core Capability Match, Preferred Qualification Match, and Evidence
  Confidence as qualitative `STRONG`, `PARTIAL`, `WEAK`, or `NOT_ASSESSED` values until a
  calibrated numeric model exists;
- original and tailored Resume Alignment;
- strong matches, partial matches, and true gaps;
- unsupported claims added count and details;
- formatting/ATS validation status;
- fidelity mode (`PRESERVED` or `RECONSTRUCTED`);
- original and tailored page counts;
- generated artifact metadata.

Do not manufacture percentages for dimensions the scoring system does not support. The existing
Candidate Fit number and Resume Alignment numbers may remain numeric because they already have
defined scoring implementations.

## 10. Step 20: review and user control

The default review view shows meaningful proposed changes with before/after text, reason,
requirement, evidence, and safety state. An advanced view exposes all audited differences.

The user may accept, reject, restore, or manually edit each change. Manual text must pass the
same semantic-drift, fabrication, metric, and length checks as an AI proposal.

Review produces a new immutable change-set revision. Generating after any disposition change
creates a new artifact version and reruns all validation. A download labeled application-ready
is available only for the latest reviewed artifact with aggregate status `PASS`. A `WARNING`
artifact may be downloaded only with its warning clearly displayed. A `FAIL` artifact is not
offered as ready to submit.

For DOCX, source paragraph indices are authoritative. For PDF-only freeform output, the existing
similarity matcher may propose pairings, but ambiguous matches must be marked for review rather
than silently assigned.

## 11. API and UI behavior

The API exposes operations to:

- create a tailoring preview/run;
- retrieve the report, validation, and change set;
- update change dispositions or manual text;
- regenerate and validate artifacts;
- download a specific immutable artifact version.

Existing `/tailor/preview` behavior remains backward compatible during migration. New fields are
additive until Streamlit and other consumers move to the shared result model.

Streamlit must call the shared pipeline for both DOCX and PDF sources. It may not route DOCX
uploads through the freeform PDF reconstruction path. The UI defaults to a concise report and
meaningful changes, with diagnostics behind expanders.

## 12. Testing requirements

### 12.1 Unit and integration fixtures

Add anonymized DOCX and PDF fixtures covering:

- mixed fonts and inline emphasis;
- right-aligned dates and tab stops;
- paragraph borders/horizontal rules;
- one-page and two-page originals;
- Unicode and linked contact information;
- multiple jobs and education entries;
- bullets containing metrics;
- deliberate overflow, duplication, truncation, placeholders, and unsupported claims.

### 12.2 Required assertions

Tests must prove:

- DOCX immutable layout signatures remain equal after approved edits;
- page-count growth fails;
- missing contact, employer, date, education, metric, or bullet fails;
- corruption and non-extractable PDFs fail;
- visual drift outside edited regions fails;
- conversion unavailability produces an honest warning/failure state;
- the correction loop runs at most once;
- Candidate Fit does not change during tailoring;
- report dimensions use qualitative values when uncalibrated;
- DOCX change records come from authoritative edits;
- rejecting/restoring a change removes it from regenerated output;
- manual edits pass the same safety gates;
- artifact versions are immutable and traceable;
- deterministic filenames are sanitized;
- Streamlit and API adapters return equivalent core results.

Run the complete product and API suites before and after implementation. The pre-change baseline
is 548 product tests and 39 API tests.

## 13. Real-world acceptance test

Use one anonymized real DOCX resume, one anonymized real PDF-only resume, and a real job posting.
For each source:

1. run Steps 10-20;
2. review every proposed change;
3. reject at least one change and manually edit another;
4. regenerate;
5. inspect the DOCX/PDF visually and extract its text;
6. verify report values and artifact lineage.

Acceptance requires no fabricated claims, all identity/job/education data present, no lost
metrics or bullets, preserved page count, no clipping/overlap, accurate changes, and a final
report that keeps Candidate Fit separate from Resume Alignment.

The PDF-only result may pass with `RECONSTRUCTED` fidelity; it must not claim exact visual
preservation.

## 14. Rollout and compatibility

Implement in independently testable slices:

1. shared domain models and richer validation;
2. DOCX layout signatures and authoritative changes;
3. visual PDF validation and bounded correction;
4. unified report;
5. persistence and artifact versioning;
6. review/disposition API and UI;
7. adapter migration and real-world acceptance.

Database additions are additive. Existing resume-file history remains unchanged. Existing
tailoring response fields remain during migration and are removed only under a separately
approved compatibility decision.

## 15. Definition of done

Steps 16-20 are complete when:

1. both entry points use the shared artifact pipeline;
2. DOCX output preserves immutable structure and page count;
3. PDF-only output is honestly labeled reconstructed;
4. generated files are searchable, ATS-readable, safely named, and versioned;
5. validation reports structured `PASS`, `WARNING`, or `FAIL` results;
6. structural, content, truth, ATS, and visual failures are caught;
7. one bounded correction is attempted only for correctable overflow;
8. Candidate Fit and Resume Alignment are separate and accurate;
9. the final report is shared across API and Streamlit;
10. changes include reason, requirement, evidence, and safety status;
11. accept/reject/restore/manual-edit behavior regenerates and revalidates output;
12. originals and prior artifact versions are never overwritten;
13. the full automated suites pass;
14. the anonymized DOCX and PDF real-world acceptance runs pass with limitations reported
    honestly.
