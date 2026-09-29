# Decision 019: Use an evidence workbench for Job Copilot's interface

**Date:** 2026-09-28  
**Status:** Accepted and implemented

## Context

The product's tailoring, discovery, artifact-validation, and application-tracking capabilities were functional, but the Streamlit interface exposed them as separate technical pages. New users saw numbered setup sections, long limitation banners, and a combined Applications page. The interface did not consistently distinguish verified facts, unknown values, true job gaps, resume alignment, and real submission capability.

The external UI prompt proposed useful interaction patterns, but also proposed replacement backend schemas and autonomous submission behavior that conflict with the existing architecture and decisions 012, 014, 015, 016, and 017.

## Decision

Use an **evidence workbench** visual and information architecture while preserving the product layer unchanged.

The five user-facing workspaces are:

1. Fact Vault
2. Job Discovery
3. Tailoring Studio
4. Apply Launchpad
5. Application Tracker

All workspaces use one semantic system for verified, review-required, blocked, and unknown states. A persistent evidence ribbon derives progress from session evidence rather than navigation. Unknown fit, compensation, and sponsorship are displayed as “Not assessed” or “Not stated,” never zero.

Tailoring Studio keeps Candidate Fit separate from Resume Alignment, excludes true gaps from proposed edits, and puts review controls before the artifact surface on narrow screens. Apply Launchpad recommends Manual mode and retains the hard `ATSCapability.final_submission` gate. Tracker reads immutable submission snapshots and shows status provenance.

## Alternatives rejected

- **Build the attachment's replacement backend and schemas.** Rejected because it would duplicate tested product logic and fragment truth/safety rules.
- **Move to React during this redesign.** Rejected because the Streamlit presentation layer can deliver the required clarity without a framework migration or new dependency.
- **Keep Applications as one tabbed page.** Rejected because staging an application and managing a portfolio are different jobs with different primary actions.
- **Show one opaque match score.** Rejected because strong evidence, partial evidence, and true gaps are needed for trustworthy decisions.
- **Style Assist/Auto as available but add warning copy.** Rejected because visual availability would contradict the actual submission capability gate.

## Visual system

The interface uses Atkinson Hyperlegible with system fallbacks, a cool paper/canvas palette, square structural panels, and semantic accents: action blue, verified green, review amber, and blocked red. Borders and spacing carry hierarchy; decorative gradients, generic floating-card grids, all-caps eyebrows, and load animations were deliberately omitted.

During the final critique, the combined Applications tabs and repeated numbered setup treatments were removed. Those treatments added interface chrome without helping the user decide what to do next.

## Verification

- Product suite: **715 passed**.
- API suite: **60 passed** (existing dependency deprecation warnings remain).
- Browser-verified Tailoring Studio, Fact Vault, Job Discovery, Apply Launchpad, and Application Tracker at desktop width.
- Browser-verified the empty Tailoring Studio at a 390×844 viewport: content remains readable, the navigation uses Streamlit's drawer, the evidence ribbon remains a single scrollable sequence, and actions use the available width.
- Verified the Tailoring Studio navigation link from a secondary page returns to the main app.
- Independent whole-branch review found and drove fixes for hidden gap proposals, misleading Manual-mode actions, evidence-ribbon state, and lost tracker context; the re-review approved with no Critical or Important findings.
- No real resume or personal data was used during visual verification.

## Honest limitations

- Manual mode remains the only reliable real application path.
- Assist/Auto cannot complete modern JavaScript-rendered ATS forms and stays hard-gated.
- Fact Vault still requires the local FastAPI service for authentication and persistence.
- Browser verification covered empty/synthetic states; it did not submit an external application.
- A public deployment URL is not claimed until one is verified.
