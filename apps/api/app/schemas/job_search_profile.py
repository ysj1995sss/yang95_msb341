from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.goals import SponsorshipPreference

ProfileStatus = Literal["active", "paused"]
WorkArrangement = Literal["onsite", "hybrid", "remote"]


class JobSearchGoals(BaseModel):
    """The preference payload for one named job-search profile. Reuses
    every field name from app.schemas.goals.JobGoals (the existing
    single-profile schema, left untouched for backward compatibility with
    jobs/ranking.py) so the two never drift into competing vocabularies for
    the same concepts, extended with the fields the product spec calls for
    that JobGoals doesn't have."""

    titles: list[str] = Field(default_factory=list)
    target_functions: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    experience_levels: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    work_arrangements: list[WorkArrangement] = Field(default_factory=list)
    relocation_preference: bool = False
    salary_min: int | None = None
    salary_preferred: int | None = None
    employment_types: list[str] = Field(default_factory=list)
    company_types: list[str] = Field(default_factory=list)
    target_companies: list[str] = Field(default_factory=list)
    exclude_companies: list[str] = Field(default_factory=list)
    sponsorship_preference: SponsorshipPreference = "show_all"
    keywords_include: list[str] = Field(default_factory=list)
    keywords_exclude: list[str] = Field(default_factory=list)


class JobSearchProfileIn(BaseModel):
    name: str
    goals: JobSearchGoals = Field(default_factory=JobSearchGoals)


class JobSearchProfileOut(BaseModel):
    id: str
    name: str
    status: ProfileStatus
    goals: JobSearchGoals
    created_at: datetime
    updated_at: datetime
