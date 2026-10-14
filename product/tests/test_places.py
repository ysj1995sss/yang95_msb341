"""Location filter (dogfood round 5, 2026-10-13): "United States", offered as a suggestion, found only
postings that spell it out, about a quarter of the US jobs a search had. Postings name a place many ways."""

import pytest

from resume_tailorer.job_search.places import canonical_place, place_matches


@pytest.mark.parametrize("location", [
    "San Francisco, California, United States", "Remote - USA", "Remote US", "Remote U.S.",
    "Mountain View, CA, USA", "Foster City, CA", "New York, NY (HQ)", "Washington, DC",
    "San Francisco, CA | New York City, NY", "Austin, Texas", "Seattle", "San Francisco",
    "Washington, D.C.", "San Francisco Bay Area",
])
def test_united_states_finds_postings_that_name_it_another_way(location):
    assert place_matches(location, "United States")
    assert place_matches(location, "USA")


@pytest.mark.parametrize("location", [
    "Barcelona, CT, Spain", "Toronto, Canada", "London, United Kingdom", "Remote", "Remote, Global",
    "Bengaluru, India", "Paris, IDF, France", "", None,
])
def test_united_states_leaves_out_other_countries_and_unstated_places(location):
    assert not place_matches(location, "United States")


def test_a_state_matches_its_name_or_its_abbreviation():
    assert place_matches("San Francisco, CA", "California")
    assert place_matches("Mountain View, CA, USA", "California")
    assert place_matches("San Francisco, California, United States", "CA")
    assert not place_matches("Chicago, IL", "CA")  # two letters no longer match inside "Chicago"
    assert not place_matches("Barcelona, CT, Spain", "Connecticut")


def test_canada_and_the_uk_by_province_or_other_name():
    assert place_matches("Toronto, ON", "Canada")
    assert place_matches("Vancouver, British Columbia", "Canada")
    assert not place_matches("London, ON", "United Kingdom")
    assert place_matches("London, UK", "United Kingdom")
    assert place_matches("Edinburgh, Scotland", "UK")


def test_a_city_and_state_typed_together():
    assert place_matches("San Francisco, California, United States", "San Francisco, CA")
    assert not place_matches("San Francisco, CA", "San Jose, CA")


def test_anything_else_still_matches_part_of_the_location():
    assert place_matches("Remote - US", "remote")
    assert place_matches("New York City, NY", "New York")
    assert place_matches("anywhere", "")
    assert place_matches("SF Bay Area", "SF")  # two letters that aren't a state still match as typed
    assert not place_matches("Berlin, Germany", "Munich")


def test_suggestions_use_one_name_per_country():
    assert canonical_place("USA") == "United States"
    assert canonical_place("U.S.") == "United States"
    assert canonical_place("UK") == "United Kingdom"
    assert canonical_place("San Francisco") == "San Francisco"
