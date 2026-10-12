# 038: Separate named-platform qualification from project/tool attribution

Date: 2026-10-11. Spec 016, approved implementation. Local branch only.

## Choice

Keep the existing requirement statuses and matcher, with explicit named products and
conjunction/alternative/example semantics. An unknown explicit platform is Check yourself,
not generic analytics evidence. The shared named-tool vocabulary protects existing products
such as Alteryx and SQL Server as well as Tableau/Qualtrics.

For new tool-use claims, exact original activity evidence is required. Global skills or
another project do not authorize a rewrite. Both artifact paths, refinement, manual editing,
Accept/regeneration and the final PDF gate enforce this. Skills/summary context is distinct;
new employer/project associations are not justified by a broad skills statement. R&D is
not the R programming language. Additive review fields and legacy API JSON round trips preserve
the same context, without invented provenance for older reviews.

Rejected: prompt-only protection; profile-wide tool permission; a new paid semantic matcher.
This conservative deterministic guard may reject a legitimate but unlinked addition: the
person can correct the relevant project facts and tailor again. It does not prove every
possible semantic claim truthful. Decision 018's global diff matcher is unchanged.

## Evidence / limits

Read `discovery/experiments/2026-10-11-specs-016-018-fixes.md` for all REDs, corrected fixtures,
final 1311 product / 148 API / 23 browser counts, live observations and review limits.
The independent review produced important findings that were fixed but stopped at the owner
spending cap before final sign-off. A passing live PDF with no meaningful proposals is not a
claim of universally better model output. Finish independent review before merging/releasing.
