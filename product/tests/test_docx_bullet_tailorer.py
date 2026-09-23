import json

import pytest
from unittest.mock import MagicMock

from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.gap_analyzer import GapCategory, GapItem, GapReport
from resume_tailorer.parsers.docx_structure import Bullet
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer


@pytest.fixture
def sample_profile():
    return CareerTruthProfile(
        contact_info={"name": "Jane Doe", "email": "jane@example.com"},
        education=[],
        work_experience=[
            WorkExperience(
                employer="Acme Corp",
                title="Marketing Manager",
                dates="2022-2024",
                responsibilities=["Did a thing"],
                accomplishments=[],
            )
        ],
        skills=[],
        tools=[],
        certifications=[],
        accomplishments=[],
    )


@pytest.fixture
def sample_bullets():
    return [
        Bullet(paragraph_index=3, text="A summary paragraph describing the candidate.", section="summary"),
        Bullet(
            paragraph_index=10,
            text="Did a thing that helped the business grow substantially",
            section="work_experience",
            job_index=0,
        ),
        Bullet(
            paragraph_index=11,
            text="Did another thing that also helped the business quite a bit",
            section="work_experience",
            job_index=0,
        ),
    ]


@pytest.fixture
def sample_job_analysis():
    return JobAnalyzer().analyze("Marketing role requiring SQL and stakeholder management.")


@pytest.fixture
def sample_gap_report():
    return GapReport(
        items=[
            GapItem(
                requirement="SQL",
                category=GapCategory.B,
                reason="Supported by experience",
                candidate_evidence="Did a thing",
            )
        ],
        summary="1 gap found",
    )


def _tailorer_with_response(raw_response: str) -> DocxBulletTailorer:
    llm = MagicMock(spec=LLMClient)
    llm.complete.return_value = raw_response
    return DocxBulletTailorer(llm=llm)


class TestParseAndValidate:
    def test_well_formed_rewrite_is_applied(self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report):
        response = json.dumps(
            [
                {"paragraph_index": 3, "change": "keep", "new_text": ""},
                {"paragraph_index": 10, "change": "rewrite", "new_text": "Did a thing that helped the business grow substantially via SQL"},
                {"paragraph_index": 11, "change": "keep", "new_text": ""},
            ]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)

        edits_by_index = {e.paragraph_index: e for e in result.edits}
        assert edits_by_index[3].changed is False
        assert edits_by_index[10].changed is True
        assert edits_by_index[10].new_text == "Did a thing that helped the business grow substantially via SQL"
        assert edits_by_index[11].changed is False
        assert result.warnings == []

    def test_response_wrapped_in_markdown_code_fence_is_stripped(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        payload = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": "Rewritten"}])
        response = f"```json\n{payload}\n```"
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edits_by_index = {e.paragraph_index: e for e in result.edits}
        assert edits_by_index[10].new_text == "Rewritten"

    def test_malformed_json_falls_back_to_all_unchanged(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        tailorer = _tailorer_with_response("not json at all")
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        assert all(not e.changed for e in result.edits)
        assert len(result.warnings) == 1
        assert "malformed" in result.warnings[0].lower()

    def test_unknown_paragraph_index_is_skipped_with_warning(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        response = json.dumps([{"paragraph_index": 999, "change": "rewrite", "new_text": "x"}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        assert all(not e.changed for e in result.edits)
        assert any("999" in w or "unknown" in w.lower() for w in result.warnings)

    def test_keep_never_trusts_models_own_new_text(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        """A 'keep' entry with a (subtly different) new_text must never be
        applied -- only the ORIGINAL bullet text is used for 'keep'."""
        response = json.dumps(
            [{"paragraph_index": 10, "change": "keep", "new_text": "Did a slightly different thing"}]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.changed is False
        assert edit.new_text == "Did a thing that helped the business grow substantially"

    def test_duplicate_paragraph_index_second_occurrence_skipped(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        response = json.dumps(
            [
                {"paragraph_index": 10, "change": "rewrite", "new_text": "First"},
                {"paragraph_index": 10, "change": "rewrite", "new_text": "Second"},
            ]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.new_text == "First"
        assert any("duplicate" in w.lower() for w in result.warnings)

    def test_rewrite_with_empty_text_falls_back_to_keep(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        response = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": "   "}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.changed is False
        assert edit.new_text == "Did a thing that helped the business grow substantially"

    def test_missing_bullets_default_to_unchanged(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        response = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": "Only this one"}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        assert len(result.edits) == len(sample_bullets)
        edit_3 = next(e for e in result.edits if e.paragraph_index == 3)
        assert edit_3.changed is False

    def test_markdown_and_leading_bullet_marker_stripped_from_rewrite(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        response = json.dumps(
            [{"paragraph_index": 10, "change": "rewrite", "new_text": "- **Did a thing** using SQL"}]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.new_text == "Did a thing using SQL"

    def test_rewrite_exceeding_length_cap_is_rejected_and_kept(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        """A rewrite that blows past the 15% growth cap must be rejected in
        CODE, not just discouraged in the prompt -- confirmed live
        (2026-09-22): a real model grew one bullet 71% longer despite being
        told to keep length close, pushing a 1-page resume to 2 pages."""
        too_long = "Did a thing that helped the business grow substantially and then did quite a bit more on top of that as well"
        response = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": too_long}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.changed is False
        assert edit.new_text == "Did a thing that helped the business grow substantially"
        assert any("exceeds" in w.lower() for w in result.warnings)

    def test_empty_bullet_list_returns_empty_result_without_calling_llm(
        self, sample_profile, sample_job_analysis, sample_gap_report
    ):
        llm = MagicMock(spec=LLMClient)
        tailorer = DocxBulletTailorer(llm=llm)
        result = tailorer.tailor_bullets([], sample_profile, sample_job_analysis, sample_gap_report)
        assert result.edits == []
        llm.complete.assert_not_called()
