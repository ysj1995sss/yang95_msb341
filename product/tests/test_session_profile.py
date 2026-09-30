from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.session_profile import (
    FACT_VAULT, RESUME_UPLOAD, get_career_profile, has_verified_profile, set_career_profile,
)


def _profile(name):
    return CareerTruthProfile(
        contact_info={"name": name}, education=[],
        work_experience=[WorkExperience(employer="Acme", title="Analyst", dates="2020", responsibilities=["x"], accomplishments=[])],
        skills=["SQL"], tools=[], certifications=[], accomplishments=[],
    )


def test_fact_vault_dict_becomes_the_shared_profile_object():
    session = {}
    set_career_profile(session, _profile("Vault").to_dict(), FACT_VAULT)
    assert isinstance(get_career_profile(session), CareerTruthProfile)
    assert get_career_profile(session).name == "Vault"
    assert has_verified_profile(session)


def test_resume_upload_never_overwrites_verified_facts():
    session = {}
    set_career_profile(session, _profile("Vault"), FACT_VAULT)
    used = set_career_profile(session, _profile("Parsed"), RESUME_UPLOAD)
    assert used.name == "Vault"
    assert get_career_profile(session).name == "Vault"


def test_resume_upload_is_used_when_no_fact_vault_profile():
    session = {}
    set_career_profile(session, _profile("Parsed"), RESUME_UPLOAD)
    assert get_career_profile(session).name == "Parsed"
    assert not has_verified_profile(session)
