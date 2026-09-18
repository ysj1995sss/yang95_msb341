from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class JobSource(Enum):
    """Enum for job posting sources."""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    HANDSHAKE = "handshake"
    GREENHOUSE = "greenhouse"
    MONSTER = "monster"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"
    COMPANY_PAGES = "company_pages"


@dataclass
class SearchGoals:
    """Represents a user's job search criteria and preferences."""
    job_title: str
    industries: List[str]
    min_salary: int
    max_salary: int
    location: str
    remote_preference: str
    sponsorship_required: bool
    experience_level: str
    company_size: str
    target_companies: List[str] = field(default_factory=list)
    exclude_companies: List[str] = field(default_factory=list)
    employment_type: str = "full-time"
    relocation_willing: bool = False

    def __post_init__(self):
        """Validate search goals."""
        if self.min_salary > self.max_salary:
            raise ValueError(f"min_salary ({self.min_salary}) must be <= max_salary ({self.max_salary})")


@dataclass
class JobPosting:
    """Represents a job posting from a job source."""
    source: JobSource
    source_id: str
    company: str
    title: str
    location: str
    description: str
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_required: Optional[str] = None
    education_required: Optional[str] = None
    sponsorship_available: bool = False
    work_mode: Optional[str] = None
    url: str = ""
    ats_platform: str = "Unknown"
    raw_json: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate job posting."""
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError(
                    f"salary_min ({self.salary_min}) must be <= salary_max ({self.salary_max})"
                )

    def __hash__(self):
        """Hash based on company, title, and location."""
        return hash((self.company, self.title, self.location))

    def __eq__(self, other):
        """Equality based on company, title, and location."""
        if not isinstance(other, JobPosting):
            return NotImplemented
        return (self.company == other.company and
                self.title == other.title and
                self.location == other.location)


@dataclass
class UserSelection:
    """Represents a user's interaction with a job posting."""
    job_posting_id: str
    action: str
    timestamp: datetime = field(default_factory=datetime.now)
    user_notes: str = ""
