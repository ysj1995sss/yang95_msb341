from typing import Literal

from pydantic import BaseModel, Field

JobSource = Literal["linkedin", "handshake", "indeed", "greenhouse", "api"]


class JobUpsertIn(BaseModel):
    company: str
    title: str
    location: str
    description: str = ""
    work_mode: str | None = None
    salary: str | None = None
    posted_at: str | None = None
    deadline: str | None = None
    employment_type: str | None = None
    sponsorship: str | None = None
    source: JobSource
    original_url: str
    ats_platform: str | None = None
    discovered_at: str
    external_ids: dict[str, str] = Field(default_factory=dict)


class JobUpsertOut(BaseModel):
    job_id: str
    user_job_id: str
    created: bool


JobStateValue = Literal["interested", "saved", "skipped"]


class JobStateIn(BaseModel):
    state: JobStateValue


class JobStateOut(BaseModel):
    job_id: str
    state: JobStateValue


class JobListItem(BaseModel):
    job_id: str
    user_job_id: str
    state: str
    fit_score: float | None = None
    company: str
    title: str
    location: str
    description: str = ""
    work_mode: str | None = None
    salary: str | None = None
    posted_at: str | None = None
    deadline: str | None = None
    employment_type: str | None = None
    sponsorship: str | None = None
    source: JobSource
    original_url: str
    ats_platform: str | None = None
    discovered_at: str
    external_ids: dict[str, str] = Field(default_factory=dict)
