from resume_tailorer.applications.models import ApplicationMode
from resume_tailorer.applications.streamlit_views import preview_token
from resume_tailorer.models import CareerTruthProfile, WorkExperience


def _profile(skill):
    return CareerTruthProfile(
        contact_info={"name": "A"}, education=[],
        work_experience=[WorkExperience(employer="Acme", title="PM", dates="2020", responsibilities=["x"], accomplishments=[])],
        skills=[skill], tools=[], certifications=[], accomplishments=[],
    )


def test_preview_approval_is_bound_to_job_resume_profile_and_mode(tmp_path):
    resume = tmp_path / "r.pdf"
    resume.write_bytes(b"v1")
    base = preview_token("job_A", str(resume), _profile("SQL"), ApplicationMode.MANUAL)

    assert preview_token("job_A", str(resume), _profile("SQL"), ApplicationMode.MANUAL) == base
    assert preview_token("job_B", str(resume), _profile("SQL"), ApplicationMode.MANUAL) != base
    assert preview_token("job_A", str(resume), _profile("Python"), ApplicationMode.MANUAL) != base
    assert preview_token("job_A", str(resume), _profile("SQL"), ApplicationMode.ASSIST) != base
    resume.write_bytes(b"v2")
    assert preview_token("job_A", str(resume), _profile("SQL"), ApplicationMode.MANUAL) != base
