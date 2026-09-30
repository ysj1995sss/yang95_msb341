from resume_tailorer.analyzers import JobAnalyzer
from resume_tailorer.analyzers.jd_sections import classify_heading, split_sections

MONGO_STYLE = """We are hiring a Product Marketing Manager.
What You’ll Do
- Own positioning for the developer data platform
- Launch features with product and sales
We’re Excited About You Because
- You have 5+ years of product marketing experience
- You write clearly for technical audiences
Bonus Points:
- Experience with databases
About MongoDB
MongoDB is an equal opportunities employer.
Req ID: 123
"""

OPENAI_STYLE = """ABOUT THE TEAM
We build products.
IN THIS ROLE, YOU WILL:
- Lead launches for enterprise customers
YOU MIGHT THRIVE IN THIS ROLE IF YOU HAVE:
- 7+ years of experience in B2B product marketing
- Experience with regulated industries
About OpenAI
OpenAI is an AI research and deployment company.
We are an equal opportunity employer.
"""


def test_title_case_headings_without_colons_split_sections():
    sections = split_sections(MONGO_STYLE)
    assert sections["responsibilities"] == [
        "Own positioning for the developer data platform",
        "Launch features with product and sales",
    ]
    assert sections["required"] == [
        "You have 5+ years of product marketing experience",
        "You write clearly for technical audiences",
    ]
    assert sections["preferred"] == ["Experience with databases"]


def test_company_and_legal_text_never_become_requirements():
    analysis = JobAnalyzer().analyze(OPENAI_STYLE)
    assert analysis.required_qualifications == [
        "7+ years of experience in B2B product marketing",
        "Experience with regulated industries",
    ]
    assert analysis.responsibilities == ["Lead launches for enterprise customers"]
    assert not any("equal opportunity" in q.lower() for q in analysis.required_qualifications)


def test_heading_classification():
    assert classify_heading("Preferred Qualifications:") == "preferred"
    assert classify_heading("Required Skills and Experience::") == "required"
    assert classify_heading("Who You Are:") == "required"
    assert classify_heading("What You'll Do") == "responsibilities"
    assert classify_heading("Benefits & Growth:") == "other"
    assert classify_heading("About MongoDB") == "other"


def test_inline_headings_and_plain_text_without_headings_still_work():
    inline = "Requirements: 3+ years of SQL\nResponsibilities: Build dashboards\n"
    assert split_sections(inline) == {
        "required": ["3+ years of SQL"], "preferred": [], "responsibilities": ["Build dashboards"],
    }
    assert split_sections("Just a paragraph about the job with no headings.") is None


def test_paragraph_after_a_bulleted_list_ends_the_section():
    text = (
        "Qualifications:\n- 5+ years in fintech marketing\n- SQL\n"
        "Plaid is proud to be an equal opportunity employer and values diversity.\n"
        "Pay Transparency Notice: Base salary varies by location.\n"
    )
    assert split_sections(text)["required"] == ["5+ years in fintech marketing", "SQL"]


def test_sections_written_as_plain_sentences_are_kept():
    text = "What you'll need:\nFive years of marketing experience.\nComfort with data.\n"
    assert split_sections(text)["required"] == ["Five years of marketing experience.", "Comfort with data."]


def test_more_real_heading_names_and_legal_text_boundary():
    text = (
        "What we look for:\n- 7+ years of product marketing\n"
        "YOU MIGHT BE A GREAT FIT IF YOU…\n- Have launched developer products\n"
        "Experience:\n5 years in B2B SaaS.\n"
        "Linear is an equal opportunity employer. We do not discriminate.\n"
    )
    assert split_sections(text)["required"] == [
        "7+ years of product marketing",
        "Have launched developer products",
        "5 years in B2B SaaS.",
    ]
