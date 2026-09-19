import pytest
from resume_tailorer.applications.form_filler import FormFiller
from resume_tailorer.applications.models import FormField
from resume_tailorer.models.career_profile import CareerTruthProfile, EducationEntry, WorkExperience


def _make_profile():
    return CareerTruthProfile(
        contact_info={
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "phone": "555-123-4567",
            "location": "San Francisco, CA",
        },
        education=[
            EducationEntry(degree="BS", field="Computer Science", institution="MIT", year=2020),
        ],
        work_experience=[
            WorkExperience(
                employer="TechCorp",
                title="Software Engineer",
                dates="2020-2023",
                responsibilities=["Built APIs"],
                accomplishments=["Reduced latency by 30%"],
            ),
        ],
        skills=["Python", "SQL"],
        tools=["Docker", "AWS"],
        certifications=["AWS Solutions Architect"],
        accomplishments=[],
    )


def test_fill_form_maps_first_name():
    filler = FormFiller()
    fields = [FormField(field_name="first_name", field_type="text", required=True)]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "Jane"
    assert filled[0].prefilled is True


def test_fill_form_maps_last_name():
    filler = FormFiller()
    fields = [FormField(field_name="last_name", field_type="text")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "Doe"
    assert filled[0].prefilled is True


def test_fill_form_maps_full_name_field():
    filler = FormFiller()
    fields = [FormField(field_name="full_name", field_type="text")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "Jane Doe"


def test_fill_form_maps_email():
    filler = FormFiller()
    fields = [FormField(field_name="email", field_type="email", required=True)]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "jane.doe@example.com"
    assert filled[0].prefilled is True


def test_fill_form_maps_phone():
    filler = FormFiller()
    fields = [FormField(field_name="phone_number", field_type="phone")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "555-123-4567"


def test_fill_form_maps_location():
    filler = FormFiller()
    fields = [FormField(field_name="location", field_type="text")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "San Francisco, CA"


def test_fill_form_maps_current_employer():
    filler = FormFiller()
    fields = [FormField(field_name="current_company", field_type="text")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "TechCorp"


def test_fill_form_maps_current_title():
    filler = FormFiller()
    fields = [FormField(field_name="current_title", field_type="text")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "Software Engineer"


def test_fill_form_leaves_unknown_field_unfilled():
    """A field with no confident mapping (e.g., a custom essay question) is never guessed."""
    filler = FormFiller()
    fields = [FormField(field_name="why_do_you_want_this_role", field_type="textarea")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == ""
    assert filled[0].prefilled is False


def test_fill_form_never_fabricates_value_not_in_profile():
    """Confirm the filled value, when present, always traces back to the profile — never invented."""
    filler = FormFiller()
    fields = [
        FormField(field_name="first_name", field_type="text"),
        FormField(field_name="email", field_type="email"),
    ]
    filled = filler.fill_form(fields, _make_profile())
    profile = _make_profile()
    for f in filled:
        if f.prefilled:
            assert f.value in profile.contact_info.get("name", "") or f.value == profile.contact_info["email"] or f.value in profile.contact_info["name"].split()

def test_fill_form_returns_new_list_not_mutating_input():
    filler = FormFiller()
    original_fields = [FormField(field_name="email", field_type="email")]
    filled = filler.fill_form(original_fields, _make_profile())
    assert original_fields[0].value == ""  # input untouched
    assert filled[0].value == "jane.doe@example.com"  # output is a new object

def test_fill_form_handles_empty_field_list():
    filler = FormFiller()
    assert filler.fill_form([], _make_profile()) == []

def test_fill_form_preserves_required_flag():
    filler = FormFiller()
    fields = [FormField(field_name="email", field_type="email", required=True)]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].required is True


def test_fill_form_company_name_field_maps_to_employer_not_candidate_name():
    """A "company_name" field asks about the candidate's employer, not their own name."""
    filler = FormFiller()
    fields = [FormField(field_name="company_name", field_type="text")]
    filled = filler.fill_form(fields, _make_profile())
    assert filled[0].value == "TechCorp"
    assert filled[0].prefilled is True


def test_fill_form_single_word_name_leaves_last_name_unfilled():
    """A single-word name (no last name) must not spill into the last_name field."""
    filler = FormFiller()
    profile = CareerTruthProfile(
        contact_info={
            "name": "Madonna",
            "email": "madonna@example.com",
            "phone": "555-000-0000",
            "location": "New York, NY",
        },
        education=[],
        work_experience=[],
        skills=[],
        tools=[],
        certifications=[],
        accomplishments=[],
    )
    fields = [FormField(field_name="last_name", field_type="text")]
    filled = filler.fill_form(fields, profile)
    assert filled[0].value == ""
    assert filled[0].prefilled is False


def test_fill_form_full_name_variant_fields_still_work():
    """Removing the bare generic "name" fallback must not break specific full-name aliases."""
    filler = FormFiller()
    for field_name in ("full_name", "candidate_name", "applicant_name"):
        fields = [FormField(field_name=field_name, field_type="text")]
        filled = filler.fill_form(fields, _make_profile())
        assert filled[0].value == "Jane Doe"
        assert filled[0].prefilled is True
