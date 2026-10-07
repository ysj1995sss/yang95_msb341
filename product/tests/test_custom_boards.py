"""Spec 013: a person's added boards, stored in their profile record."""

from datetime import datetime

from resume_tailorer.job_search import custom_boards as cb

NOW = datetime(2026, 10, 6, 9, 30)


def _lever(count=2):
    def fetch(url):
        assert url.startswith("https://api.lever.co/v0/postings/")
        return 200, [{"id": str(i)} for i in range(count)]
    return fetch


def _not_found(url):
    return 404, {"ok": False}


def test_verified_board_is_saved_with_provenance():
    record = {}
    result = cb.add_board(record, "https://jobs.lever.co/northwind/abc", fetch=_lever(), now=NOW)
    assert result.ok and result.code == "added"
    (board,) = cb.boards_in(record)
    assert board["id"] == "lever:northwind" and board["name"] == "Northwind"
    assert board["source_url"] == "https://jobs.lever.co/northwind/abc"
    assert board["verified_at"] == "2026-10-06T09:30:00" and board["postings_at_check"] == 2
    assert board["industry"] == "Not specified" and board["last_search"] is None


def test_person_can_name_and_label_a_board():
    record = {}
    result = cb.add_board(record, "jobs.lever.co/nw", name=" Northwind Outdoor ", industry="Retail", fetch=_lever())
    assert result.board["name"] == "Northwind Outdoor" and result.board["industry"] == "Retail"
    assert "Northwind Outdoor" in result.message
    assert cb.industry_labels(cb.boards_in(record)) == {"northwind outdoor": "Retail"}


def test_unknown_industry_label_is_not_saved():
    record = {}
    cb.add_board(record, "jobs.lever.co/nw", industry="Space Pirates", fetch=_lever())
    assert cb.boards_in(record)[0]["industry"] == "Not specified"


def test_unverified_boards_are_never_saved():
    record = {}
    result = cb.add_board(record, "jobs.lever.co/northwind", fetch=_not_found)
    assert not result.ok and result.code == "not_found"
    assert cb.boards_in(record) == []


def test_link_problems_do_not_touch_the_network():
    def never(url):
        raise AssertionError("fetched")

    result = cb.add_board({}, "https://careers.northwind.example/", fetch=never)
    assert result.code == "link" and not result.ok


def test_duplicates_are_refused_before_fetching():
    record = {}
    cb.add_board(record, "jobs.lever.co/Northwind", fetch=_lever())

    def never(url):
        raise AssertionError("fetched")

    result = cb.add_board(record, "https://jobs.lever.co/northwind/xyz", fetch=never)
    assert result.code == "duplicate" and len(cb.boards_in(record)) == 1


def test_curated_boards_are_already_searched():
    def never(url):
        raise AssertionError("fetched")

    result = cb.add_board({}, "https://boards.greenhouse.io/GitLab", fetch=never)
    assert result.code == "curated" and "GitLab (Greenhouse) is already searched by default" in result.message


def test_cap_of_added_boards():
    record = {cb.FIELD: [{"platform": "lever", "token": f"co{i}"} for i in range(cb.MAX_CUSTOM_BOARDS)]}
    result = cb.add_board(record, "jobs.lever.co/one-more", fetch=_lever())
    assert result.code == "limit" and str(cb.MAX_CUSTOM_BOARDS) in result.message


def test_remove_and_legacy_records():
    assert cb.boards_in({}) == [] and cb.boards_in(None) == []
    assert cb.boards_in({cb.FIELD: [{"platform": "myspace", "token": "x"}, "junk", {"platform": "lever"}]}) == []
    record = {}
    cb.add_board(record, "jobs.lever.co/northwind", fetch=_lever())
    assert cb.remove_board(record, "lever:northwind") is True
    assert cb.remove_board(record, "lever:northwind") is False
    assert cb.boards_in(record) == []


def test_grouping_and_search_results():
    record = {}
    cb.add_board(record, "jobs.lever.co/northwind", fetch=_lever())
    cb.add_board(record, "jobs.lever.co/contoso", name="Contoso", fetch=_lever())
    grouped = cb.extra_boards(cb.boards_in(record))
    assert grouped == {"lever": {"northwind": ("Northwind", "Not specified"), "contoso": ("Contoso", "Not specified")}}
    cb.record_search_results(record, {"lever:northwind": {"status": "ok", "matched": 3},
                                      "lever:contoso": {"status": "not_found"}}, "2026-10-06T10:00:00")
    by_id = {b["id"]: b["last_search"] for b in cb.boards_in(record)}
    assert by_id["lever:northwind"] == {"at": "2026-10-06T10:00:00", "status": "ok", "matched": 3}
    assert by_id["lever:contoso"]["status"] == "not_found"
    assert cb.added_board_keys(cb.boards_in(record)) == {("lever", "northwind"), ("lever", "contoso")}
