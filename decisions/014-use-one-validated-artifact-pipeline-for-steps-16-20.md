# Decision 014: Use one validated artifact pipeline for Steps 16-20

**Date:** 2026-09-27
**Status:** Active

## Context

An audit of Steps 16-20 found that the DOCX master-template splice path already preserves the
most important structural properties, but the rest of the workflow is fragmented. Streamlit
always uses the freeform reconstruction path, FastAPI selects DOCX versus PDF correctly, PDF
validation checks only a few technical properties, report construction is duplicated, changes
are display-only, and generated artifacts are not versioned.

The product needs a closed workflow from approved content through preserved/generated documents,
validation, reporting, review, regeneration, and immutable artifact storage. Rebuilding the
existing DOCX splice engine would discard working architecture and contradict decisions 006,
009, and 013.

## Options considered

1. **Patch Streamlit and FastAPI independently.** Fastest for individual gaps, but preserves two
   orchestration paths and guarantees further drift in validation, reporting, and diffs.
2. **Build one shared validated-artifact pipeline in `product/resume_tailorer/`.** Reuse the DOCX
   splice and freeform PDF engines behind shared models for changes, validation, reports, and
   artifacts; keep Streamlit and FastAPI as adapters.
3. **Replace document generation with a new document-layout system.** Could eventually support
   more templates, but needlessly rebuilds the strongest existing component and adds high
   regression risk.

## Decision

Choose option 2.

DOCX originals continue to use the original file as the immutable master template. PDF-only
originals continue through controlled reconstruction and are labeled `RECONSTRUCTED`, not
falsely described as visually preserved. Both paths produce the same structured validation,
report, change-set, lineage, and artifact result.

Validation becomes a real gate with `PASS`, `WARNING`, and `FAIL` outcomes. It covers structure,
content, truthfulness, ATS extraction, page count, and deterministic render-based visual checks.
PyMuPDF will be added as the rendering dependency because the current pypdf/reportlab stack can
read and create PDFs but cannot rasterize them for visual inspection.

The correction loop is bounded to one retry and only handles correctable content overflow. It
never shrinks fonts/margins or retries unsupported claims, corruption, missing identity data,
conversion failure, or immutable-layout drift.

Candidate Fit remains unchanged by tailoring and separate from Resume Alignment. Uncalibrated
report dimensions use qualitative categories instead of invented precision.

Generated artifacts and review revisions are immutable and traceable to the original resume
version, profile snapshot/version, job snapshot, tailoring run, change set, and validation result.

Full requirements are in `specs/002-steps-16-20-validated-artifact-pipeline.md`.

## Consequences

- Steps 16-20 gain one source of truth rather than additional entry-point-specific fixes.
- API/database schemas grow additively to persist runs and artifacts.
- Streamlit must migrate to the shared DOCX/PDF dispatch rather than always using freeform
  reconstruction.
- Visual validation adds PyMuPDF to both product and API environments.
- The work must ship in independently tested slices because review controls and artifact
  persistence depend on the validation/change models but should not block their initial use.

## What would change our mind

If PyMuPDF proves nondeterministic or unsafe for the supported local runtime, replace only the
rendering adapter while keeping the validation model and pipeline boundary. If real usage shows
that persisting binary artifacts in the local database creates unacceptable size or performance
costs, move bytes to a content-addressed local store while retaining immutable database metadata
and checksums.
