import json

import pytest
from unittest.mock import MagicMock

from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.gap_analyzer import GapCategory, GapItem, GapReport
from resume_tailorer.parsers.docx_structure import Bullet
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer

# Long enough that a short, safe addition (e.g. " via SQL") stays within the
# 15% length-growth cap while every content word below is preserved --
# avoids two hard-reject checks (length cap, semantic drift) fighting each
# other in these fixtures purely because the base bullet was too short to
# have room for both a realistic addition AND every original word intact.
_BULLET_10_TEXT = "Did a thing that helped the business grow substantially over the past two fiscal years"
_BULLET_11_TEXT = "Did another thing that also helped the business quite a bit"


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
        Bullet(paragraph_index=10, text=_BULLET_10_TEXT, section="work_experience", job_index=0),
        Bullet(paragraph_index=11, text=_BULLET_11_TEXT, section="work_experience", job_index=0),
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
        rewritten = _BULLET_10_TEXT + " via SQL"
        response = json.dumps(
            [
                {"paragraph_index": 3, "change": "keep", "new_text": ""},
                {"paragraph_index": 10, "change": "rewrite", "new_text": rewritten},
                {"paragraph_index": 11, "change": "keep", "new_text": ""},
            ]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)

        edits_by_index = {e.paragraph_index: e for e in result.edits}
        assert edits_by_index[3].changed is False
        assert edits_by_index[10].changed is True
        assert edits_by_index[10].new_text == rewritten
        assert edits_by_index[11].changed is False
        assert result.warnings == []

    def test_response_wrapped_in_markdown_code_fence_is_stripped(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        rewritten = _BULLET_10_TEXT + " via SQL"
        payload = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": rewritten}])
        response = f"```json\n{payload}\n```"
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edits_by_index = {e.paragraph_index: e for e in result.edits}
        assert edits_by_index[10].new_text == rewritten

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
        assert edit.new_text == _BULLET_10_TEXT

    def test_duplicate_paragraph_index_second_occurrence_skipped(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        first = _BULLET_10_TEXT + " via SQL"
        second = _BULLET_10_TEXT + " via BI"
        response = json.dumps(
            [
                {"paragraph_index": 10, "change": "rewrite", "new_text": first},
                {"paragraph_index": 10, "change": "rewrite", "new_text": second},
            ]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.new_text == first
        assert any("duplicate" in w.lower() for w in result.warnings)

    def test_rewrite_with_empty_text_falls_back_to_keep(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        response = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": "   "}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.changed is False
        assert edit.new_text == _BULLET_10_TEXT

    def test_missing_bullets_default_to_unchanged(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        response = json.dumps(
            [{"paragraph_index": 10, "change": "rewrite", "new_text": _BULLET_10_TEXT + " via SQL"}]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        assert len(result.edits) == len(sample_bullets)
        edit_3 = next(e for e in result.edits if e.paragraph_index == 3)
        assert edit_3.changed is False

    def test_markdown_and_leading_bullet_marker_stripped_from_rewrite(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        rewritten = _BULLET_10_TEXT + " via SQL"
        response = json.dumps(
            [{"paragraph_index": 10, "change": "rewrite", "new_text": f"- **{rewritten}**"}]
        )
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.new_text == rewritten

    def test_rewrite_exceeding_length_cap_is_rejected_and_kept(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        """A rewrite that blows past the 15% growth cap must be rejected in
        CODE, not just discouraged in the prompt -- confirmed live
        (2026-09-22): a real model grew one bullet 71% longer despite being
        told to keep length close, pushing a 1-page resume to 2 pages."""
        too_long = _BULLET_10_TEXT + " and then did quite a bit more on top of that as well, over and over again"
        response = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": too_long}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.changed is False
        assert edit.new_text == _BULLET_10_TEXT
        assert any("exceeds" in w.lower() for w in result.warnings)

    def test_rewrite_dropping_a_core_word_is_rejected_and_kept(
        self, sample_bullets, sample_profile, sample_job_analysis, sample_gap_report
    ):
        """The exact bug found live (2026-09-23): 'grow' silently replaced
        with a different word, narrowing the claim -- rejected in CODE,
        not just discouraged in the prompt, matching the length-cap
        precedent above."""
        narrowed = _BULLET_10_TEXT.replace("grow", "expand")
        response = json.dumps([{"paragraph_index": 10, "change": "rewrite", "new_text": narrowed}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(sample_bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = next(e for e in result.edits if e.paragraph_index == 10)
        assert edit.changed is False
        assert edit.new_text == _BULLET_10_TEXT
        assert any("semantic drift" in w.lower() for w in result.warnings)

    def test_competency_reorder_is_applied(
        self, sample_profile, sample_job_analysis, sample_gap_report
    ):
        bullets = [
            Bullet(
                paragraph_index=20,
                text="Core Competencies: Strategic Thinker | Market Research | Project Management",
                section="competencies",
            )
        ]
        reordered = "Core Competencies: Project Management | Strategic Thinker | Market Research"
        response = json.dumps([{"paragraph_index": 20, "change": "rewrite", "new_text": reordered}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = result.edits[0]
        assert edit.changed is True
        assert edit.new_text == reordered

    def test_competency_reorder_that_drops_an_item_is_rejected(
        self, sample_profile, sample_job_analysis, sample_gap_report
    ):
        bullets = [
            Bullet(
                paragraph_index=20,
                text="Core Competencies: Strategic Thinker | Market Research | Project Management",
                section="competencies",
            )
        ]
        # Missing "Market Research" -- not a pure reorder.
        dropped = "Core Competencies: Project Management | Strategic Thinker"
        response = json.dumps([{"paragraph_index": 20, "change": "rewrite", "new_text": dropped}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = result.edits[0]
        assert edit.changed is False
        assert edit.new_text == bullets[0].text
        assert any("item set changed" in w.lower() for w in result.warnings)

    def test_competency_reorder_that_adds_a_new_item_is_rejected(
        self, sample_profile, sample_job_analysis, sample_gap_report
    ):
        bullets = [
            Bullet(
                paragraph_index=20,
                text="Core Competencies: Strategic Thinker | Market Research | Project Management",
                section="competencies",
            )
        ]
        added = "Core Competencies: Strategic Thinker | Market Research | Project Management | Leadership"
        response = json.dumps([{"paragraph_index": 20, "change": "rewrite", "new_text": added}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = result.edits[0]
        assert edit.changed is False

    def test_rewrite_adding_unverified_characterization_is_rejected_and_kept(
        self, sample_profile, sample_job_analysis, sample_gap_report
    ):
        """The exact bug found live (2026-09-23): 'loyalty' added to
        describe a program the profile never characterizes that way, even
        though 'loyalty' appears in the job description -- rejected in
        CODE, not just discouraged in the prompt."""
        bullets = [
            Bullet(
                paragraph_index=15,
                text="Built a customer acquisition and experience framework targeting growth",
                section="work_experience",
                job_index=0,
            )
        ]
        unverified = "Built a customer acquisition and loyalty experience framework targeting growth"
        response = json.dumps([{"paragraph_index": 15, "change": "rewrite", "new_text": unverified}])
        tailorer = _tailorer_with_response(response)
        result = tailorer.tailor_bullets(bullets, sample_profile, sample_job_analysis, sample_gap_report)
        edit = result.edits[0]
        assert edit.changed is False
        assert edit.new_text == bullets[0].text
        assert any("unverified" in w.lower() for w in result.warnings)

    def test_empty_bullet_list_returns_empty_result_without_calling_llm(
        self, sample_profile, sample_job_analysis, sample_gap_report
    ):
        llm = MagicMock(spec=LLMClient)
        tailorer = DocxBulletTailorer(llm=llm)
        result = tailorer.tailor_bullets([], sample_profile, sample_job_analysis, sample_gap_report)
        assert result.edits == []
        llm.complete.assert_not_called()
