"""Tests for shared job field normalization."""

from resume_tailorer.job_search.normalize import (
    NOT_STATED,
    POSSIBLE,
    UNKNOWN,
    YES,
    NO,
    normalize_company,
    normalize_location,
    normalize_sponsorship,
    normalize_title,
)


def test_sponsorship_none_is_not_stated():
    assert normalize_sponsorship(None) == NOT_STATED


def test_sponsorship_empty_string_is_not_stated():
    assert normalize_sponsorship("") == NOT_STATED
    assert normalize_sponsorship("   ") == NOT_STATED


def test_sponsorship_bool_mapping():
    assert normalize_sponsorship(True) == YES
    assert normalize_sponsorship(False) == NO


def test_sponsorship_from_description_text():
    assert normalize_sponsorship("We offer H-1B sponsorship") == YES
    assert normalize_sponsorship("No sponsorship available") == NO
    assert normalize_sponsorship("Sponsorship may be available") == POSSIBLE


def test_sponsorship_unknown_noise():
    assert normalize_sponsorship("great benefits package") == UNKNOWN


def test_normalize_company_title_location_casefold():
    assert normalize_company("  Acme Inc. ") == normalize_company("acme inc.")
    assert normalize_title("Software Engineer") == normalize_title("software engineer")
    assert normalize_location("New York, NY") == normalize_location("new york, ny")
