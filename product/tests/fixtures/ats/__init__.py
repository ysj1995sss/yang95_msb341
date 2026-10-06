"""Anonymized ATS acceptance fixtures (spec 010). Names, employers and numbers are invented."""

from pathlib import Path

from resume_tailorer.models import CareerTruthProfile, EducationEntry, WorkExperience

HERE = Path(__file__).parent
POSTING = (HERE / "posting_marketing_analyst.txt").read_text(encoding="utf-8")

# Confirmed: the current role, education, skills. Unconfirmed: the older role (imported, never
# reviewed), which is the only place Salesforce appears.
PROVENANCE = {
    "contact_info.name": "confirmed",
    "work_experience[0]": "confirmed",
    "work_experience[1]": "resume",
    "education[0]": "confirmed",
    "skills": "confirmed",
    "tools": "confirmed",
}


def profile() -> CareerTruthProfile:
    return CareerTruthProfile(
        contact_info={"name": "Riley Park", "email": "riley.park@example.com", "location": "Denver, CO"},
        education=[EducationEntry(degree="BS", field="Economics", institution="State University", year=2019)],
        work_experience=[
            WorkExperience(
                employer="Acme Retail", title="Marketing Analyst", dates="Jan 2022 - Present",
                responsibilities=[
                    "Built SQL dashboards used by 40 regional managers to track weekly campaign results",
                    "Led on-time delivery of a 6-month store launch across 4 teams, with weekly risk reviews",
                    "Acted as PM (project manager) for the 2024 loyalty program redesign",
                ],
                accomplishments=["Raised email campaign conversion 12% by redesigning audience segments"],
            ),
            WorkExperience(
                employer="Bluebird Goods", title="Marketing Coordinator", dates="Jun 2019 - Dec 2021",
                responsibilities=["Cleaned Salesforce campaign data before each quarterly review"],
                accomplishments=[],
            ),
        ],
        skills=["SQL", "Snowflake", "Excel", "Segmentation"],
        tools=["Google Analytics"],
        certifications=[],
        accomplishments=[],
        summary="Marketing analyst who turns campaign data into decisions.",
    )
