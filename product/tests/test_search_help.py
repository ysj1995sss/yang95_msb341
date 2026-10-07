"""Spec 013: filters that explain themselves, accurate board counts, and the sponsorship fix."""

from datetime import datetime

import pytest

from resume_tailorer.job_search.database import JobDatabase
from resume_tailorer.job_search.models import JobPosting, JobSource, SearchGoals
from resume_tailorer.ui import search_help as sh
from resume_tailorer.ui.job_view import SPONSORSHIP_NOT_STATED, build_row


def _job(source_id, company="Acme Retail", sponsorship=None, raw=None, location="Remote - US"):
    return JobPosting(source=JobSource.GREENHOUSE, source_id=source_id, company=company, title="Data Analyst",
                      location=location, description="x", posted_date=datetime(2026, 10, 1), salary_min=None,
                      salary_max=None, experience_required="Unknown", education_required="Unknown",
                      sponsorship_available=sponsorship, work_mode="Unknown",
                      url=f"https://job-boards.greenhouse.io/acme/jobs/{source_id}", ats_platform="Greenhouse",
                      raw_json=raw or {})


def _goals(**kw):
    base = dict(job_title="Data Analyst", industries=[], min_salary=0, max_salary=0, location="",
                remote_preference="any", sponsorship_required=False, experience_level=[], company_size="")
    return SearchGoals(**{**base, **kw})


@pytest.fixture
def db(tmp_path):
    database = JobDatabase(str(tmp_path / "jobs.db"))
    database.create_tables()
    database.save_job_posting(_job("1", sponsorship=None))
    database.save_job_posting(_job("2", company="Contoso", sponsorship=True))
    database.save_job_posting(_job("3", company="Fabrikam", sponsorship=False))
    yield database
    database.close()


def test_sponsorship_hides_only_jobs_that_say_no(db):
    ids = sorted(j.source_id for j in db.search_jobs(_goals(sponsorship_required=True)))
    assert ids == ["1", "2"]


def test_company_filters_ignore_case_and_spaces(db):
    assert [j.source_id for j in db.search_jobs(_goals(target_companies=[" acme retail "]))] == ["1"]
    assert sorted(j.source_id for j in db.search_jobs(_goals(exclude_companies=["CONTOSO"]))) == ["1", "3"]
    assert db.search_jobs(_goals(target_companies=["Acme"])) == []  # a filter, not a fuzzy search


def test_rows_mark_added_boards_and_unstated_sponsorship():
    job = _job("1", raw={"board": "Acme"})
    row = build_row(job, None, None, added_keys={("greenhouse", "acme")}, sponsorship_needed=True)
    assert row.added_board and row.source == "Greenhouse · board you added"
    assert row.sponsorship_note == SPONSORSHIP_NOT_STATED
    plain = build_row(job, None, None)
    assert not plain.added_board and plain.sponsorship_note == "" and plain.source == "Greenhouse"
    stated = build_row(_job("2", sponsorship=True), None, None, sponsorship_needed=True)
    assert stated.sponsorship_note == ""


def test_board_counts_follow_sources_and_added_boards():
    gh, lever = sh.curated_count("greenhouse"), sh.curated_count("lever")
    added = [{"platform": "lever", "token": "northwind"}, {"platform": "ashby", "token": "contoso"}]
    assert sh.boards_in_scope(["greenhouse", "lever"], []) == gh + lever
    assert sh.boards_in_scope(["greenhouse"], added) == gh + 2
    assert sh.boards_in_scope(["greenhouse"], added, include_custom=False) == gh
    assert sh.boards_in_scope([], added) == 2
    assert sh.source_label("lever") == f"Lever: {lever} curated companies"
    assert sh.searching_text(1) == "Searching 1 company board"


def test_board_status_texts():
    assert sh.board_status({"postings_at_check": 3})[0] == "Verified with 3 open postings; not searched yet"
    ok = {"last_search": {"at": "2026-10-06T10:00:00", "status": "ok", "matched": 1}}
    assert sh.board_status(ok) == ("1 matching role at the last search (Oct 6)", "verified")
    gone = sh.board_status({"last_search": {"at": "2026-10-06T10:00:00", "status": "not_found"}})
    assert gone[1] == "blocked" and "remove it or paste its new link" in gone[0]
    assert sh.board_status({"last_search": {"status": "failed"}})[1] == "review"


def test_search_result_line_names_failed_added_boards():
    boards = [{"platform": "greenhouse", "token": "Northwind", "name": "Northwind"},
              {"platform": "lever", "token": "ok-co", "name": "OK Co"}]
    failed = sh.failed_added_boards(boards, {"greenhouse:northwind": {"status": "not_found"},
                                             "lever:ok-co": {"status": "ok"}})
    assert failed == ["Northwind (Greenhouse)"]
    assert sh.search_result_line(41, 2, failed) == "Searched 41 boards; 2 didn't answer, including Northwind (Greenhouse)."
    assert sh.search_result_line(41, 1, failed) == "Searched 41 boards; 1 didn't answer: Northwind (Greenhouse)."
    assert sh.search_result_line(75, 0) == "Searched 75 boards."
    assert sh.search_result_line(0, 0) == ""


def test_unknown_company_notes():
    notes = sh.unknown_company_notes("gitlab, Northwind Outdoor, Stripe", ["greenhouse"],
                                     [{"platform": "lever", "token": "nw", "name": "Northwind Outdoor"}])
    assert len(notes) == 1 and "Stripe" in notes[0] and "Add its career board" in notes[0]
    assert sh.unknown_company_notes("GitLab", ["lever"], []) != []  # GitLab is on Greenhouse, unticked


@pytest.mark.parametrize("title, expected", [
    ("Senior Data Analyst", ["Data Analyst", "Senior Analyst"]),
    ("Data Analyst II", ["Data Analyst", "Analyst II"]),
    ("Senior Product Marketing Manager", ["Product Marketing Manager", "Senior Marketing Manager",
                                          "Senior Product Manager"]),
    ("Head of Product", ["Product"]),
    ("Analyst", []),
    ("", []),
])
def test_broader_titles_keep_the_role(title, expected):
    assert sh.broader_titles(title) == expected


def test_narrowing_names_filters_that_hide_roles():
    form = {"job_title": "Data Analyst", "location": "New York", "remote_preference": "remote",
            "sponsorship_required": False, "industries": ["Finance"], "min_salary": 0}

    def count(f):
        return 0 + (4 if not f["location"] else 0) + (1 if not f["industries"] else 0)

    found = sh.narrowing(form, 0, count)
    assert [(item["key"], item["extra"]) for item in found] == [("location", 4), ("industries", 1)]
    assert found[0]["text"] == "Location “New York” is hiding 4 more roles."
    assert sh.narrowing(form, 5, count) == []  # enough results: nothing shown
    assert sh.cleared(form, "location")["location"] == "" and sh.cleared(form, "nope") == form


def test_detail_labels_an_added_board_like_the_list():
    from resume_tailorer.ui.job_view import build_detail

    job = _job("1", company="Northwind Outdoor", raw={"board": "northwind"})
    detail = build_detail(job, None, None, added_keys={("greenhouse", "northwind")},
                          industry_labels={"northwind outdoor": "Retail"})
    facts = dict(detail.facts)
    assert detail.row.source == "Greenhouse · board you added" and facts["Source"] == detail.row.source
    assert facts["Industry"] == "Retail"
    plain = dict(build_detail(job, None, None).facts)
    assert plain["Source"] == "Greenhouse" and plain["Industry"] == "Not specified"
