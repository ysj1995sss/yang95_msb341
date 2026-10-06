"""What Job Copilot's "ATS" checks are, and aren't (spec 010). One text for both apps: the
Streamlit pages read it directly and the web app gets it from the API, so they can't drift."""

from __future__ import annotations

TITLE = "About ATS checks"

PARAGRAPHS = (
    "Employers use different applicant tracking systems, set up in different ways. There is no "
    "universal ATS score or passing threshold, and Job Copilot can't see or predict any "
    "employer's ranking.",
    "What Job Copilot can do: check that your resume file reads back cleanly as text on this "
    "computer, and help you show real evidence for the job's most important requirements in "
    "clear words.",
    "It never adds a skill, credential, number or result you haven't shown, and it never hides "
    "keywords. Requirements you don't have stay visible as gaps.",
)

TERMS_NOTE = "This is a word check against your Career Profile, not an employer's ATS score."

OVERLAP_NOTE = (
    "Keyword overlap is Job Copilot's own estimate (60% of the posting's listed skills and tools "
    "found, 40% of its first five required qualifications covered). It is not an employer score "
    "and isn't a target."
)


def as_dict() -> dict:
    return {"title": TITLE, "paragraphs": list(PARAGRAPHS), "terms_note": TERMS_NOTE, "overlap_note": OVERLAP_NOTE}
