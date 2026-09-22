from typing import Literal

from pydantic import BaseModel, Field

SponsorshipPreference = Literal["required", "preferred", "none_needed", "show_all"]


class JobGoals(BaseModel):
    titles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    experience_levels: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    remote_preference: str = ""
    salary_min: int | None = None
    company_types: list[str] = Field(default_factory=list)
    target_companies: list[str] = Field(default_factory=list)
    exclude_companies: list[str] = Field(default_factory=list)
    sponsorship_preference: SponsorshipPreference = "show_all"
