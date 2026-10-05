"""Requests from one person at the same time (two tabs; React's double fetch in development)
must not share one SQLite connection across threads (found 2026-10-05: /v2/home answered 500,
'bad parameter or other API misuse')."""

from concurrent.futures import ThreadPoolExecutor


def test_simultaneous_requests_from_one_person_all_succeed(workspace_client):
    paths = ["/v2/home", "/v2/jobs", "/v2/tracker", "/v2/apply"] * 15

    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = list(pool.map(lambda path: workspace_client.get(path).status_code, paths))

    assert codes == [200] * len(paths)
