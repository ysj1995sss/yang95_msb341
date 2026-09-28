import pytest
from resume_tailorer.applications.ats_parsers.base_parser import BaseATSParser
from resume_tailorer.applications.ats_parsers.greenhouse_parser import GreenhouseParser
from resume_tailorer.applications.ats_parsers.lever_parser import LeverParser
from resume_tailorer.applications.ats_parsers.ashby_parser import AshbyParser
from resume_tailorer.applications.ats_parsers.workday_parser import WorkdayParser


SAMPLE_FORM_HTML = """
<html><body>
<form>
    <label for="first_name">First Name</label>
    <input type="text" id="first_name" name="first_name" required>

    <label for="last_name">Last Name</label>
    <input type="text" id="last_name" name="last_name" required>

    <label for="email">Email</label>
    <input type="email" id="email" name="email" required>

    <label for="phone">Phone</label>
    <input type="tel" id="phone" name="phone">

    <label for="cover_letter">Cover Letter</label>
    <textarea id="cover_letter" name="cover_letter"></textarea>

    <label for="work_authorization">Are you authorized to work in the US?</label>
    <select id="work_authorization" name="work_authorization">
        <option value="yes">Yes</option>
        <option value="no">No</option>
    </select>

    <label for="agree">I agree to the terms</label>
    <input type="checkbox" id="agree" name="agree">
</form>
</body></html>
"""


def test_base_ats_parser_is_abstract():
    with pytest.raises(TypeError):
        BaseATSParser()


def test_greenhouse_parser_platform_name():
    parser = GreenhouseParser()
    assert parser.get_platform_name() == "greenhouse"
    assert parser.is_supported() is True


def test_lever_parser_platform_name():
    parser = LeverParser()
    assert parser.get_platform_name() == "lever"
    assert parser.is_supported() is True


def test_ashby_parser_platform_name():
    parser = AshbyParser()
    assert parser.get_platform_name() == "ashby"
    assert parser.is_supported() is True


def test_greenhouse_lever_ashby_declare_no_final_submission_capability():
    """Decision 012 proved real forms are JS-rendered SPAs a static fetch
    can't see -- no platform may claim it can actually complete a real
    submission until that's proven otherwise (decision 016)."""
    for parser in (GreenhouseParser(), LeverParser(), AshbyParser()):
        cap = parser.get_capability()
        assert cap.manual_supported is True
        assert cap.final_submission is False
        assert cap.assist_supported is False
        assert cap.auto_supported is False
        assert cap.resume_upload is False


def test_greenhouse_declares_profile_prefill_capability():
    # Prefill logic itself is real and correct for whatever fields a page
    # exposes -- the gap is that pages expose almost none, not that
    # prefill is broken.
    assert GreenhouseParser().get_capability().profile_prefill is True


def test_workday_declares_no_capability_beyond_manual():
    cap = WorkdayParser().get_capability()
    assert cap.manual_supported is True
    assert cap.profile_prefill is False
    assert cap.final_submission is False


def test_workday_parser_reports_unsupported():
    parser = WorkdayParser()
    assert parser.get_platform_name() == "workday"
    assert parser.is_supported() is False


def test_workday_parser_returns_empty_fields():
    """Workday forms are JS-rendered SPAs; static HTML parsing can't find real fields."""
    parser = WorkdayParser()
    fields = parser.parse_form(SAMPLE_FORM_HTML)
    assert fields == []


def test_greenhouse_parser_extracts_text_fields():
    parser = GreenhouseParser()
    fields = parser.parse_form(SAMPLE_FORM_HTML)

    field_names = {f.field_name for f in fields}
    assert "first_name" in field_names
    assert "last_name" in field_names
    assert "email" in field_names
    assert "phone" in field_names


def test_greenhouse_parser_detects_required_fields():
    parser = GreenhouseParser()
    fields = parser.parse_form(SAMPLE_FORM_HTML)

    by_name = {f.field_name: f for f in fields}
    assert by_name["first_name"].required is True
    assert by_name["phone"].required is False


def test_greenhouse_parser_detects_field_types():
    parser = GreenhouseParser()
    fields = parser.parse_form(SAMPLE_FORM_HTML)

    by_name = {f.field_name: f for f in fields}
    assert by_name["email"].field_type == "email"
    assert by_name["phone"].field_type == "phone"
    assert by_name["cover_letter"].field_type == "textarea"
    assert by_name["work_authorization"].field_type == "select"
    assert by_name["agree"].field_type == "checkbox"


def test_greenhouse_parser_fields_start_unfilled():
    parser = GreenhouseParser()
    fields = parser.parse_form(SAMPLE_FORM_HTML)
    assert all(f.value == "" and f.prefilled is False for f in fields)


def test_lever_parser_extracts_same_generic_fields():
    """Lever/Ashby share the generic extraction logic — same HTML, same result shape."""
    parser = LeverParser()
    fields = parser.parse_form(SAMPLE_FORM_HTML)
    field_names = {f.field_name for f in fields}
    assert "email" in field_names
    assert "cover_letter" in field_names


def test_parser_handles_malformed_html_gracefully():
    parser = GreenhouseParser()
    fields = parser.parse_form("<html><body><form><input type='text' name='x'</form>")
    # BeautifulSoup is lenient with malformed HTML; should not raise
    assert isinstance(fields, list)


def test_parser_handles_empty_html():
    parser = GreenhouseParser()
    fields = parser.parse_form("")
    assert fields == []


def test_parser_ignores_hidden_and_submit_inputs():
    html = """
    <form>
        <input type="hidden" name="csrf_token" value="abc123">
        <input type="submit" value="Apply">
        <input type="text" name="first_name">
    </form>
    """
    parser = GreenhouseParser()
    fields = parser.parse_form(html)
    field_names = {f.field_name for f in fields}
    assert "csrf_token" not in field_names
    assert "first_name" in field_names
