"""Spec 013: recognizing pasted career-board links and verifying boards (no network)."""

import pytest

from resume_tailorer.job_search.board_links import (
    NOT_FOUND,
    UNCONFIRMED,
    UNREACHABLE,
    VERIFIED,
    VERIFIED_EMPTY,
    BoardRef,
    LinkProblem,
    parse_board_link,
    verify_board,
)


@pytest.mark.parametrize("link, platform, token", [
    ("https://boards.greenhouse.io/northwind", "greenhouse", "northwind"),
    ("https://job-boards.greenhouse.io/northwind/jobs/4012345?gh_src=x", "greenhouse", "northwind"),
    ("boards.greenhouse.io/embed/job_board?for=northwind&b=https://x", "greenhouse", "northwind"),
    ("https://boards.greenhouse.io/embed/job_app?for=northwind&token=99", "greenhouse", "northwind"),
    ("https://boards-api.greenhouse.io/v1/boards/northwind/jobs", "greenhouse", "northwind"),
    ("http://www.jobs.lever.co/northwind", "lever", "northwind"),
    ("https://jobs.lever.co/northwind/1a2b-3c4d/apply", "lever", "northwind"),
    ("https://jobs.ashbyhq.com/Northwind.Outdoor/abc-123/application", "ashby", "Northwind.Outdoor"),
    ("https://jobs.smartrecruiters.com/NorthwindGroup/7440000-data-analyst", "smartrecruiters", "NorthwindGroup"),
    ("https://careers.smartrecruiters.com/NorthwindGroup", "smartrecruiters", "NorthwindGroup"),
    ("  https://jobs.lever.co/northwind#top  ", "lever", "northwind"),
])
def test_recognizes_supported_links(link, platform, token):
    ref = parse_board_link(link)
    assert isinstance(ref, BoardRef)
    assert (ref.platform, ref.token) == (platform, token)
    assert ref.id == f"{platform}:{token.lower()}"


@pytest.mark.parametrize("link, words", [
    ("", "Paste a link"),
    ("https://careers.northwind.example/jobs?gh_jid=123", "company's own site"),
    ("https://job-boards.eu.greenhouse.io/northwind", "European"),
    ("https://jobs.eu.lever.co/northwind", "European"),
    ("https://northwind.wd5.myworkdayjobs.com/en-US/careers", "Workday"),
    ("https://www.linkedin.com/jobs/view/123", "LinkedIn"),
    ("https://www.indeed.com/viewjob?jk=1", "Indeed"),
    ("https://boards.greenhouse.io/", "doesn't name a company board"),
    ("https://boards.greenhouse.io/embed/job_board", "doesn't name a company board"),
    ("https://jobs.lever.co/<script>", "doesn't name a company board"),
    ("ftp://jobs.lever.co/northwind", "doesn't look like a link"),
])
def test_explains_links_it_cannot_use(link, words):
    problem = parse_board_link(link)
    assert isinstance(problem, LinkProblem)
    assert words in problem.message


def test_unsupported_and_company_site_messages_offer_the_paste_path():
    for link in ("https://careers.northwind.example/", "https://northwind.icims.com/jobs"):
        assert "Paste its description in Tailor" in parse_board_link(link).message


def _fetcher(answers):
    calls = []

    def fetch(url):
        calls.append(url)
        for prefix, answer in answers.items():
            if url.startswith(prefix):
                return answer
        raise AssertionError(f"unexpected fetch {url}")

    fetch.calls = calls
    return fetch


GH = "https://boards-api.greenhouse.io/v1/boards/northwind"


def test_greenhouse_verified_with_stated_name():
    fetch = _fetcher({GH + "/jobs": (200, {"jobs": [{"id": 1}, {"id": 2}]}), GH: (200, {"name": "Northwind Outdoor"})})
    result = verify_board(parse_board_link("boards.greenhouse.io/northwind"), fetch)
    assert (result.outcome, result.name, result.postings) == (VERIFIED, "Northwind Outdoor", 2)
    assert result.ok and "2 open postings" in result.message
    assert all(url.startswith("https://boards-api.greenhouse.io/") for url in fetch.calls)


def test_greenhouse_empty_board_is_still_real():
    fetch = _fetcher({GH + "/jobs": (200, {"jobs": []}), GH: (200, {"name": "Northwind"})})
    result = verify_board(parse_board_link("boards.greenhouse.io/northwind"), fetch)
    assert result.outcome == VERIFIED_EMPTY and result.ok


def test_greenhouse_unknown_board():
    result = verify_board(parse_board_link("boards.greenhouse.io/northwind"), _fetcher({GH: (404, {"error": "x"})}))
    assert result.outcome == NOT_FOUND and not result.ok and "no public board called 'northwind'" in result.message


@pytest.mark.parametrize("answer", [(None, None), (500, None), (200, "not json"), (200, {"oops": 1})])
def test_lever_unreachable_or_odd_answers_are_not_saved(answer):
    result = verify_board(parse_board_link("jobs.lever.co/northwind"), _fetcher({"https://api.lever.co/": answer}))
    assert result.outcome == UNREACHABLE and not result.ok and "Nothing was saved" in result.message


def test_lever_verified_name_from_identifier():
    fetch = _fetcher({"https://api.lever.co/v0/postings/north-wind": (200, [{"id": "a"}])})
    result = verify_board(parse_board_link("jobs.lever.co/north-wind"), fetch)
    assert (result.outcome, result.name, result.postings) == (VERIFIED, "North Wind", 1)


def test_lever_not_found_and_empty():
    lever = "https://api.lever.co/"
    assert verify_board(parse_board_link("jobs.lever.co/x"), _fetcher({lever: (404, {})})).outcome == NOT_FOUND
    assert verify_board(parse_board_link("jobs.lever.co/x"), _fetcher({lever: (200, [])})).outcome == VERIFIED_EMPTY


def test_ashby_counts_only_listed_jobs():
    fetch = _fetcher({"https://api.ashbyhq.com/": (200, {"jobs": [{"isListed": False}]})})
    assert verify_board(parse_board_link("jobs.ashbyhq.com/northwind"), fetch).outcome == VERIFIED_EMPTY
    fetch = _fetcher({"https://api.ashbyhq.com/": (404, None)})
    assert verify_board(parse_board_link("jobs.ashbyhq.com/northwind"), fetch).outcome == NOT_FOUND


def test_smartrecruiters_empty_answer_cannot_be_confirmed():
    fetch = _fetcher({"https://api.smartrecruiters.com/": (200, {"totalFound": 0, "content": []})})
    result = verify_board(parse_board_link("jobs.smartrecruiters.com/NorthwindGroup"), fetch)
    assert result.outcome == UNCONFIRMED and not result.ok and "can't be confirmed" in result.message


def test_smartrecruiters_verified_with_company_name():
    fetch = _fetcher({"https://api.smartrecruiters.com/v1/companies/NorthwindGroup/postings": (
        200, {"totalFound": 41, "content": [{"id": "1", "company": {"name": "Northwind Group"}}]})})
    result = verify_board(parse_board_link("jobs.smartrecruiters.com/NorthwindGroup"), fetch)
    assert (result.outcome, result.name, result.postings) == (VERIFIED, "Northwind Group", 41)


def test_a_failing_fetch_is_unreachable_not_an_error():
    def boom(url):
        raise RuntimeError("network down")

    assert verify_board(parse_board_link("jobs.lever.co/northwind"), boom).outcome == UNREACHABLE
