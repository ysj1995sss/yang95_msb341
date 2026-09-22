"""
Mirrors resume_tailorer.models.career_profile.CareerTruthProfile exactly,
so the stored profile JSON and the API contract are the same shape --
no adapter needed at the API boundary (unlike job-copilot, whose flatter
profile schema needed one).
"""

from pydantic import BaseModel, Field


class EducationEntryOut(BaseModel):
    degree: str = ""
    field: str = ""
    institution: str = ""
    year: int = 0
    gpa: str | None = None


class WorkExperienceOut(BaseModel):
    employer: str = ""
    title: str = ""
    dates: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    accomplishments: list[str] = Field(default_factory=list)
    location: str | None = None
    employment_type: str | None = None


class CareerTruthProfileOut(BaseModel):
    contact_info: dict = Field(default_factory=dict)
    education: list[EducationEntryOut] = Field(default_factory=list)
    work_experience: list[WorkExperienceOut] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    accomplishments: list[str] = Field(default_factory=list)
