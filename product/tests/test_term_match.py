"""Whole-term skill matching and short requirement labels (decision 027)."""

import pytest

from resume_tailorer.analyzers.term_match import mentions, short_requirement
from resume_tailorer.job_search.candidate_fit import CandidateFitScorer


@pytest.mark.parametrize("text", [
    "Own our go-to-market plan",
    "Go to market with partners",
    "Go above and beyond for customers",
    "Good judgement",
    "Built Django services",
    "on the go",
])
def test_go_is_not_found_in_ordinary_english(text):
    assert not mentions("go", text)


@pytest.mark.parametrize("text", ["Services in Go and Python", "Golang microservices", "Go, Rust"])
def test_go_the_language_is_found(text):
    assert mentions("go", text)


def test_rest_spring_and_express_need_their_technology_spelling():
    assert not mentions("rest", "Work with the rest of the team")
    assert mentions("rest", "Design REST APIs")
    assert mentions("rest", "RESTful services")
    assert not mentions("spring", "Spring 2027 internship")
    assert mentions("spring", "Java and Spring Boot")
    assert mentions("express", "Node and express.js")


def test_symbols_and_case():
    assert mentions("c++", "Modern C++ and Python")
    assert not mentions("c", "Modern C++")
    assert mentions("c#", "C# and .NET")
    assert mentions("sql", "Strong SQL skills")
    assert not mentions("sql", "PostgreSQLish")
    assert mentions("node.js", "Node.js backend")
    assert mentions("python", "Python.")


def test_go_to_market_role_does_not_require_go():
    jd = "Requirements: 3+ years in product marketing. Own the go-to-market plan and SQL reporting."
    skills = CandidateFitScorer()._extract_required_skills(jd)
    assert "go" not in skills
    assert "sql" in skills


@pytest.mark.parametrize("sentence, expected", [
    ("Strong experience with SQL and Tableau, ideally in a fast-paced environment.", "SQL and Tableau"),
    ("3+ years of experience with Python", "3+ years Python"),
    ("Ability to communicate complex findings to executives; comfortable presenting.",
     "Communicate complex findings to executives"),
    ("Familiarity with dbt (or similar tools)", "dbt"),
    ("Kubernetes", "Kubernetes"),
])
def test_short_requirement(sentence, expected):
    assert short_requirement(sentence) == expected


def test_short_requirement_caps_length():
    label = short_requirement("Experience building and scaling distributed data pipelines across many teams and regions worldwide")
    assert label.endswith("…") and len(label.split()) <= 8


def test_testing_matches_at_the_start_of_a_sentence():
    assert mentions("testing", "Testing frameworks such as pytest")
    assert not mentions("testing", "Testing the waters with new markets")


def test_a_list_requirement_keeps_every_item():
    assert short_requirement("Experience with SQL, Python, and Tableau") == "SQL, Python, and Tableau"
