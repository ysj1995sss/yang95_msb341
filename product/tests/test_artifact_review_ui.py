"""Task 8: pure, Streamlit-free review-state helpers for the shared
artifact pipeline's UI (default view hides noise; review dispositions
build the same payload shape the API's PATCH /tailor/runs/{id}/changes
endpoint expects)."""

from resume_tailorer.artifacts.models import ChangeCategory, ChangeDisposition, ResumeChange, ValidationStatus
from resume_tailorer.ui.artifact_review import build_review_payload, visible_changes


def _change(change_id, original_text, proposed_text, category=ChangeCategory.REPHRASED) -> ResumeChange:
    return ResumeChange(
        change_id=change_id, section="work_experience", source_index=None,
        original_text=original_text, proposed_text=proposed_text, category=category,
        reason="test", job_requirement="", evidence_source="career_profile",
        evidence_text=original_text, validation_status=ValidationStatus.PASS,
        disposition=ChangeDisposition.PENDING,
    )


MEANINGFUL_CHANGE = _change("c1", "Led the team", "Led a cross-functional team")
UNCHANGED_CHANGE = _change("c2", "Same text", "Same text", category=ChangeCategory.UNCHANGED)
PUNCTUATION_ONLY_CHANGE = _change("c3", "Built APIs, and tools", "Built APIs and tools.")
CHANGES = [MEANINGFUL_CHANGE, UNCHANGED_CHANGE, PUNCTUATION_ONLY_CHANGE]


class TestVisibleChanges:
    def test_default_view_hides_unchanged_and_punctuation_only_changes(self):
        assert visible_changes(CHANGES, advanced=False) == [MEANINGFUL_CHANGE]

    def test_advanced_view_shows_everything(self):
        assert visible_changes(CHANGES, advanced=True) == CHANGES

    def test_rejected_change_is_still_shown_by_default(self):
        rejected = _change("c4", "Original", "Proposed")
        rejected_variant = ResumeChange(
            **{**rejected.__dict__, "category": ChangeCategory.REJECTED},
        )
        assert rejected_variant in visible_changes([rejected_variant], advanced=False)


class TestBuildReviewPayload:
    def test_rejected_and_manual_edits_build_expected_review_payload(self):
        payload = build_review_payload(
            {"c1": "REJECTED", "c2": "MANUALLY_EDITED"},
            {"c2": "User-approved text"},
        )
        assert payload["changes"][0] == {"change_id": "c1", "disposition": "REJECTED"}
        assert payload["changes"][1]["manual_text"] == "User-approved text"

    def test_non_manual_dispositions_omit_manual_text_key(self):
        payload = build_review_payload({"c1": "ACCEPTED"}, {})
        assert "manual_text" not in payload["changes"][0]

    def test_empty_dispositions_produce_an_empty_change_list(self):
        assert build_review_payload({}, {}) == {"changes": []}
