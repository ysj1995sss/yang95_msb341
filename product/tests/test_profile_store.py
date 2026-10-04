import pytest

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.profile_import import RECORD_KEY, import_resume, load_into_session, store_for
from resume_tailorer.profile_store import (
    CONFIRMED,
    EDITED,
    FROM_RESUME,
    ProfileStore,
    apply_edits,
    confirm_remaining,
    provenance_of,
)
from resume_tailorer.session_profile import CAREER_PROFILE_KEY, FACT_VAULT, PROFILE_SOURCE_KEY

PROFILE = {
    "contact_info": {"name": "Sam Rivera", "email": "sam@example.com", "phone": "", "location": ""},
    "education": [{"degree": "BS", "field": "Economics", "institution": "State U", "year": 2018, "gpa": None, "notes": []}],
    "work_experience": [{"employer": "Northwind", "title": "Analyst", "dates": "2019-2023",
                         "responsibilities": ["Built weekly SQL reports"], "accomplishments": []}],
    "skills": ["SQL"], "tools": ["Tableau"], "certifications": [], "accomplishments": [], "summary": "",
}


class FakeParser:
    def parse(self, path):
        return CareerTruthProfile.from_dict(PROFILE)


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path))
    return tmp_path


def test_empty_store_loads_a_blank_record(tmp_path):
    record = ProfileStore(tmp_path).load()
    assert record["profile"] == {} and record["resume"] is None
    assert record["authorization"] == {"authorized_to_work": None, "sponsorship_required": None}


def test_resume_versions_are_kept_and_never_overwritten(tmp_path):
    store = ProfileStore(tmp_path)
    record = store.load()
    first = store.save_resume_file(record, "cv.docx", b"one")
    second = store.save_resume_file(record, "cv.docx", b"two")
    assert (first["version"], second["version"]) == (1, 2)
    assert store.resume_bytes(first) == b"one" and store.resume_bytes(second) == b"two"
    assert len(record["resume_history"]) == 2 and record["resume"] == second


def test_a_changed_resume_file_is_not_used(tmp_path):
    store = ProfileStore(tmp_path)
    meta = store.save_resume_file(store.load(), "cv.pdf", b"original")
    (tmp_path / meta["stored_as"]).write_bytes(b"changed")
    assert store.resume_bytes(meta) is None


def test_save_and_load_round_trip(tmp_path):
    store = ProfileStore(tmp_path)
    record = store.load()
    record["preferences"] = {"job_title": "Analyst"}
    store.save(record)
    assert ProfileStore(tmp_path).load()["preferences"] == {"job_title": "Analyst"}


def test_import_marks_facts_from_resume_and_keeps_goals(data_dir):
    store = store_for("local")
    record = store.load()
    record["preferences"] = {"job_title": "Analyst"}
    record["authorization"] = {"authorized_to_work": True, "sponsorship_required": False}
    store.save(record)
    record = import_resume(store, "cv.docx", b"bytes", parser=FakeParser())
    assert record["preferences"] == {"job_title": "Analyst"}
    assert record["authorization"]["sponsorship_required"] is False
    assert provenance_of(record, "contact_info.name") == FROM_RESUME
    assert provenance_of(record, "contact_info.phone") == "missing"
    assert record["facts_confirmed_at"] is None


def test_edits_are_marked_and_confirm_covers_the_rest(data_dir):
    record = import_resume(store_for("local"), "cv.docx", b"x", parser=FakeParser())
    edited = dict(record["profile"], skills=["SQL", "Python"])
    assert apply_edits(record, edited) == ["skills"]
    assert provenance_of(record, "skills") == EDITED
    count = confirm_remaining(record)
    assert provenance_of(record, "skills") == EDITED  # an edit is never downgraded
    assert provenance_of(record, "tools") == CONFIRMED
    assert count >= 1 and record["facts_confirmed_at"]


def test_load_into_session_makes_it_the_shared_verified_profile(data_dir):
    import_resume(store_for("local"), "cv.docx", b"x", parser=FakeParser())
    session = {}
    load_into_session(session, "local")
    assert session[PROFILE_SOURCE_KEY] == FACT_VAULT
    assert session[CAREER_PROFILE_KEY].name == "Sam Rivera"
    assert session[RECORD_KEY]["resume"]["filename"] == "cv.docx"


def test_each_owner_has_their_own_profile(data_dir):
    import_resume(store_for("alice"), "cv.docx", b"x", parser=FakeParser())
    assert store_for("bob").load()["profile"] == {}


def test_bullets_show_as_one_list_and_untouched_jobs_stay_unchanged():
    from resume_tailorer.profile_store import combined_bullets, split_bullets

    job = {"responsibilities": ["Led launches"], "accomplishments": ["Grew sales 20%"]}
    lines = combined_bullets(job)
    assert lines == ["Led launches", "Grew sales 20%"]
    assert split_bullets(job, lines) == (["Led launches"], ["Grew sales 20%"])
    assert split_bullets(job, lines + ["New bullet"]) == (["Led launches", "New bullet"], ["Grew sales 20%"])


def test_gpa_edit_is_saved_and_marked(data_dir):
    record = import_resume(store_for("local"), "cv.docx", b"x", parser=FakeParser())
    edited = dict(record["profile"], education=[dict(record["profile"]["education"][0], gpa="3.8")])
    assert apply_edits(record, edited) == ["education[0]"]
    assert record["profile"]["education"][0]["gpa"] == "3.8"


def test_tailored_resume_handoff_is_restored_only_if_the_exact_file_is_there(tmp_path):
    import hashlib

    from resume_tailorer.active_job import remember_handoff, restore_handoff
    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
    from resume_tailorer.tailoring_session import HANDOFF_KEY

    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"%PDF-1.4 tailored")
    handoff = {"job_id": "greenhouse_1", "pdf_path": str(pdf), "sha256": hashlib.sha256(b"%PDF-1.4 tailored").hexdigest(),
               "version": 2, "validation_status": "PASS", "resume_match_score": 0.8}
    record = {}
    assert remember_handoff(record, handoff, True) is True
    assert remember_handoff(record, handoff, True) is False  # unchanged, no rewrite

    session = {PENDING_TAILOR_JOB_KEY: {"job_id": "greenhouse_1"}}
    assert restore_handoff(session, record)["review_complete"] is True
    assert session[HANDOFF_KEY]["version"] == 2

    other_job = {PENDING_TAILOR_JOB_KEY: {"job_id": "greenhouse_2"}}
    assert restore_handoff(other_job, record) is None
    pdf.write_bytes(b"changed")
    assert restore_handoff({PENDING_TAILOR_JOB_KEY: {"job_id": "greenhouse_1"}}, record) is None
    failed = dict(record, active_handoff=dict(record["active_handoff"], validation_status="FAIL"))
    assert restore_handoff({PENDING_TAILOR_JOB_KEY: {"job_id": "greenhouse_1"}}, failed) is None
