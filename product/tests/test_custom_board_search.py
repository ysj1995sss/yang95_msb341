"""Spec 013: searching boards a person added, alongside (or instead of) the curated ones."""

from unittest.mock import MagicMock, patch

from resume_tailorer.job_search.job_attributes import apply_goal_filters, industry_for
from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.job_search.models import JobSource, ProviderRunStatus, SearchGoals
from resume_tailorer.job_search.scrapers import GreenhouseScraper, LeverScraper, SmartRecruitersScraper
from resume_tailorer.job_search.scrapers import board_scraper


def _goals(title="Data Analyst", industries=()):
    return SearchGoals(
        job_title=title, industries=list(industries), min_salary=0, max_salary=0, location="",
        remote_preference="any", sponsorship_required=False, experience_level=[], company_size="",
    )


def _gh_job(i, title="Data Analyst"):
    return {"id": i, "title": title, "absolute_url": f"https://job-boards.greenhouse.io/northwind/jobs/{i}",
            "location": {"name": "Remote"}, "content": "&lt;p&gt;SQL&lt;/p&gt;", "updated_at": "2026-10-01T00:00:00Z"}


def _gh_fetch(boards):
    """boards: {token: jobs list, or None for a board that didn't answer}."""
    def fetch(self, token):
        return {"jobs": boards[token]} if boards.get(token) is not None else None
    return fetch


def test_added_board_is_searched_with_its_name_and_provenance():
    scraper = GreenhouseScraper()
    boards = {"northwind": [_gh_job(1), _gh_job(2, "Chef")]}
    with patch.object(GreenhouseScraper, "board_tokens", lambda self: ["gitlab"]), \
         patch.object(GreenhouseScraper, "_fetch_board", _gh_fetch({**boards, "gitlab": []})):
        jobs = scraper.scrape(_goals(), extra_boards={"northwind": ("Northwind Outdoor", "Retail")})
    (job,) = jobs
    assert job.company == "Northwind Outdoor" and job.raw_json["board"] == "northwind"
    assert job.url == "https://job-boards.greenhouse.io/northwind/jobs/1"
    assert scraper.board_results == {"gitlab": {"status": "ok", "matched": 0},
                                     "northwind": {"status": "ok", "matched": 1}}


def test_curated_boards_can_be_left_out():
    scraper = GreenhouseScraper()
    seen = []

    def fetch(self, token):
        seen.append(token)
        return {"jobs": [_gh_job(1)]}

    with patch.object(GreenhouseScraper, "board_tokens", lambda self: ["gitlab"]), \
         patch.object(GreenhouseScraper, "_fetch_board", fetch):
        scraper.scrape(_goals(), extra_boards={"northwind": ("Northwind", "Not specified")}, include_curated=False)
    assert seen == ["northwind"]


def test_an_added_board_that_is_curated_is_searched_once():
    scraper = GreenhouseScraper()
    with patch.object(GreenhouseScraper, "board_tokens", lambda self: ["gitlab"]), \
         patch.object(GreenhouseScraper, "_fetch_board", _gh_fetch({"gitlab": [_gh_job(1)]})):
        jobs = scraper.scrape(_goals(), extra_boards={"GitLab": ("GitLab", "Technology")})
    assert len(jobs) == 1 and list(scraper.board_results) == ["gitlab"]


def test_a_board_that_404s_is_reported_not_found():
    scraper = LeverScraper()
    response = MagicMock(status_code=404)
    response.json.return_value = {"ok": False}
    with patch.object(LeverScraper, "board_tokens", lambda self: []), \
         patch("requests.get", return_value=response):
        assert scraper.scrape(_goals(), extra_boards={"gone": ("Gone Co", "Not specified")}) == []
    assert scraper.board_results == {"gone": {"status": "not_found", "matched": 0}}
    assert scraper.data_source == "unavailable"


def test_a_board_that_times_out_is_reported_failed():
    scraper = LeverScraper()
    with patch.object(LeverScraper, "board_tokens", lambda self: []), \
         patch("requests.get", side_effect=TimeoutError("slow")):
        scraper.scrape(_goals(), extra_boards={"slow": ("Slow Co", "Not specified")})
    assert scraper.board_results["slow"]["status"] == "failed"
    board_scraper.clear_board_cache()


def test_smartrecruiters_added_company():
    scraper = SmartRecruitersScraper()
    detail = {"id": "9", "name": "Data Analyst", "postingUrl": "https://jobs.smartrecruiters.com/NorthwindGroup/9",
              "company": {"name": "Northwind Group"}, "location": {"fullLocation": "Austin, TX"}}

    def fake(self, url, timeout=10):
        if url.endswith("/postings/9"):
            return detail
        if "/NorthwindGroup/postings" in url:
            return {"content": [{"id": "9", "name": "Data Analyst"}], "totalFound": 1}
        return {"content": [], "totalFound": 0}

    with patch.object(SmartRecruitersScraper, "board_tokens", lambda self: []), \
         patch.object(SmartRecruitersScraper, "_make_get_request", fake):
        (job,) = scraper.scrape(_goals(), extra_boards={"NorthwindGroup": ("Northwind Group", "Not specified")})
    assert job.raw_json["board"] == "NorthwindGroup" and job.company == "Northwind Group"
    assert scraper.board_results == {"NorthwindGroup": {"status": "ok", "matched": 1}}


def test_industry_label_for_an_added_board():
    from resume_tailorer.job_search.models import JobPosting
    from datetime import datetime

    job = JobPosting(source=JobSource.LEVER, source_id="1", company="Northwind Outdoor", title="Data Analyst",
                     location="Remote", description="x", posted_date=datetime.now(), salary_min=None,
                     salary_max=None, experience_required="Unknown", education_required="Unknown",
                     sponsorship_available=None, work_mode="Unknown", url="https://jobs.lever.co/nw/1")
    labels = {"northwind outdoor": "Retail"}
    assert industry_for(job) == "Not specified" and industry_for(job, labels) == "Retail"
    assert apply_goal_filters([job], _goals(industries=["Finance"]), industry_labels=labels) == []
    assert apply_goal_filters([job], _goals(industries=["Retail"]), industry_labels=labels) == [job]


def test_service_searches_added_boards_even_when_their_platform_is_unticked(tmp_path):
    service = JobService(db_path=str(tmp_path / "jobs.db"), applications_db_path=str(tmp_path / "apps.db"))
    boards = [{"platform": "greenhouse", "token": "northwind", "name": "Northwind", "industry": "Not specified"},
              {"platform": "greenhouse", "token": "gone", "name": "Gone Co", "industry": "Not specified"}]
    with patch.object(GreenhouseScraper, "board_tokens", lambda self: ["gitlab"]), \
         patch.object(GreenhouseScraper, "_fetch_board", _gh_fetch({"northwind": [_gh_job(1)], "gitlab": [_gh_job(5)]})), \
         patch.object(LeverScraper, "board_tokens", lambda self: ["l1", "l2"]), \
         patch.object(LeverScraper, "_fetch_board", lambda self, token: []):
        summary = service.search_and_store(_goals(), [JobSource.LEVER], custom_boards=boards)
    assert [p.source for p in summary.providers] == [JobSource.LEVER, JobSource.GREENHOUSE]
    assert all(p.status == ProviderRunStatus.OK for p in summary.providers)
    assert summary.boards_searched == 4 and summary.boards_failed == 1  # l1, l2, northwind, gone
    assert summary.custom_board_results == {"greenhouse:northwind": {"status": "ok", "matched": 1},
                                            "greenhouse:gone": {"status": "failed", "matched": 0}}
    stored = [j.company for j in service.db.search_jobs(_goals())]
    assert stored == ["Northwind"]  # gitlab (curated Greenhouse) wasn't searched
    service.close()


def test_service_without_added_boards_is_unchanged(tmp_path):
    service = JobService(db_path=str(tmp_path / "jobs.db"), applications_db_path=str(tmp_path / "apps.db"))
    with patch.object(LeverScraper, "board_tokens", lambda self: ["l1"]), \
         patch.object(LeverScraper, "_fetch_board", lambda self, token: []):
        summary = service.search_and_store(_goals(), [JobSource.LEVER])
    assert summary.boards_searched == 1 and summary.custom_board_results == {}
    service.close()
