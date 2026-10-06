"""Spec 011: the requirement review works beyond marketing and analytics, on postings without
headings, and across spelling variants. Anonymized postings and profiles."""

from resume_tailorer.analyzers.job_analyzer import JobAnalyzer, sentence_requirements
from resume_tailorer.analyzers.requirement_review import (
    CHECK, DIRECT, MENTION, NONE, PARTIAL, build_review,
)
from resume_tailorer.models import CareerTruthProfile, EducationEntry, WorkExperience

NURSING = (
    "Registered Nurse - Med/Surg. Northwind Health is hiring an RN to join our medical-surgical unit. "
    "You must have an active RN license and current BLS certification. Experience with Epic EHR is required. "
    "ACLS certification is a plus. 2+ years of acute care experience preferred. "
    "You will provide patient care, administer medications and document in the electronic health record. "
    "We offer great benefits and are an equal opportunity employer."
)

FINANCE = """Senior Accountant - Bluebird Goods

Requirements
- Bachelor's degree in Accounting or Finance.
- 3+ years of experience with GAAP financial reporting and month-end close.
- Advanced Excel and NetSuite.
- Active CPA license.

Preferred Qualifications
- Experience with SOX compliance.
- Hyperion or other FP&A tools.
"""

SOFTWARE = """Data Engineer - Acme Retail

Requirements
- Strong SQL and experience with PostgreSQL.
- Python for building data pipelines.
- Experience with Amazon Web Services.

Nice to have
- Airflow and dbt.
- PM experience working with product managers.
"""


def _profile(jobs, skills=(), tools=(), education=(), certifications=()):
    return CareerTruthProfile(
        contact_info={"name": "Riley Park", "email": "riley@example.com"},
        education=list(education), work_experience=list(jobs), skills=list(skills), tools=list(tools),
        certifications=list(certifications), accomplishments=[],
    )


def _row(review, start):
    return next(r for r in review.rows if r.text.startswith(start))


def test_requirement_sentences_are_found_in_a_posting_without_headings():
    required, preferred = sentence_requirements(NURSING)
    assert any("RN license" in r for r in required) and any("Epic" in r for r in required)
    assert any("ACLS" in p for p in preferred) and any("acute care" in p for p in preferred)
    assert not any("benefits" in s or "You will provide" in s for s in required + preferred)


def test_nursing_review_reads_licenses_tools_and_partial_credentials():
    nurse = _profile(
        [WorkExperience(employer="Northwind Health", title="Staff Nurse", dates="2021 - Present",
                        responsibilities=["Charted patient care in Epic for a 30-bed med/surg unit",
                                          "Administered medications and triaged admissions"], accomplishments=[])],
        certifications=["RN license (Colorado)", "BLS"],
        education=[EducationEntry(degree="BSN", field="Nursing", institution="State University", year=2020)],
    )
    review = build_review(JobAnalyzer().analyze(NURSING), nurse, posting=NURSING)
    license_row = _row(review, "You must have an active RN license")
    assert license_row.status == DIRECT and dict(license_row.term_status) == {"RN": DIRECT, "BLS": DIRECT}
    assert license_row.hard_gate
    assert _row(review, "Experience with Epic EHR").status in (DIRECT, PARTIAL)
    assert _row(review, "ACLS certification is a plus").status == NONE


def test_finance_review_with_variants_and_a_missing_credential():
    accountant = _profile(
        [WorkExperience(employer="Acme Retail", title="Staff Accountant", dates="2020 - Present",
                        responsibilities=["Led month end close and GAAP financial reporting for 3 entities",
                                          "Built reconciliations in MS Excel"], accomplishments=[])],
        tools=["NetSuite"],
        education=[EducationEntry(degree="BS", field="Accounting", institution="State University", year=2019)],
    )
    review = build_review(JobAnalyzer().analyze(FINANCE), accountant, posting=FINANCE)
    assert _row(review, "Bachelor's degree").status == DIRECT
    assert _row(review, "3+ years of experience with GAAP").status == DIRECT
    excel = _row(review, "Advanced Excel and NetSuite")
    assert excel.status == PARTIAL and dict(excel.term_status) == {"Excel": DIRECT, "NetSuite": MENTION}
    cpa = _row(review, "Active CPA license")
    assert cpa.status == NONE and cpa.hard_gate


def test_software_review_matches_spelling_variants_and_flags_an_ambiguous_acronym():
    engineer = _profile(
        [WorkExperience(employer="Northwind", title="Data Engineer", dates="2021 - Present",
                        responsibilities=["Built Python data pipelines into a Postgres warehouse with complex SQL",
                                          "Deployed pipelines on Amazon Web Services (AWS)",
                                          "Worked with the PM (project manager) on delivery dates"],
                        accomplishments=[])],
        skills=["Airflow"],
    )
    review = build_review(JobAnalyzer().analyze(SOFTWARE), engineer, posting=SOFTWARE)
    assert _row(review, "Strong SQL and experience with PostgreSQL").status == DIRECT  # Postgres = PostgreSQL
    assert _row(review, "Python for building data pipelines").status == DIRECT
    assert _row(review, "Experience with Amazon Web Services").status == DIRECT
    airflow = _row(review, "Airflow and dbt")
    assert dict(airflow.term_status) == {"Airflow": MENTION, "dbt": NONE}
    assert _row(review, "PM experience").status == CHECK
