# 039: File selection does not change the source of confirmed facts

Date: 2026-10-11. Spec 017, approved implementation. Local branch only.

## Choice

Resolve one frozen effective fact context for a run. When a saved Career Profile takes
precedence, carry its confirmation provenance and canonical content hash even with a one-off
file. Preserve the canonical role order for requirement provenance/hash before Word alignment.
An independent upload without saved master facts has no Career Profile hash and does not
create/update the master record.

Record the selected filename/type, file source and effective fact source with the review.
Both frontends show Resume file and Facts separately before a run and in its saved review.
Selecting another file does not relabel an existing review. Legacy metadata remains unknown.
Text rendering escapes user-controlled filenames. One-off Word files supply layout and
existing bullets without a promise of full profile sync; PDF rebuilding uses effective facts.

Rejected: silently treating an upload as permission to confirm optional facts; an upload
override/merge feature; relabeling old reviews from the current selection. The existing
Career Profile precedence and batch rule requiring its master resume are retained.

## Evidence / limits

The stale warning was reproduced as absent on a one-off run using canonical facts. New API
cases verify changed-profile blocking, unchanged master facts, unconfirmed optional facts,
independent uploads, selection/removal and frozen review filenames. The combined browser case
verifies the visible labels and source snapshot. See the specs-016–018 experiment for exact
full-suite results and the incomplete independent final review. No human test is claimed.
