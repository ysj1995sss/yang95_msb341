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


class TriageAction(Enum):
    """Canonical user triage decisions (Step 9)."""
    UNREVIEWED = "unreviewed"
    SAVE = "save"
    APPLY = "apply"
    PASS = "pass"


_TRIAGE_ALIASES = {
    "unreviewed": TriageAction.UNREVIEWED,
    "save": TriageAction.SAVE,
    "saved": TriageAction.SAVE,
    "interested": TriageAction.SAVE,
    "apply": TriageAction.APPLY,
    "applied": TriageAction.APPLY,
    "pass": TriageAction.PASS,
    "skipped": TriageAction.PASS,
    "skip": TriageAction.PASS,
    "discovered": TriageAction.UNREVIEWED,
}


def canonicalize_triage_action(raw: str | None) -> TriageAction:
    """Map legacy or canonical triage strings to TriageAction."""
    if raw is None or not str(raw).strip():
        return TriageAction.UNREVIEWED
    key = str(raw).strip().lower()
    return _TRIAGE_ALIASES.get(key, TriageAction.UNREVIEWED)


def triage_storage_value(action: TriageAction) -> str:
    """Canonical string written to DB / API state."""
    return action.value


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
    # None = not stated (honest unknown); True/False only when source says so.
    sponsorship_available: Optional[bool] = None
    work_mode: Optional[str] = None
    url: str = ""
    ats_platform: str = "Unknown"
    raw_json: Dict[str, Any] = field(default_factory=dict)
    alternative_sources: List[str] = field(default_factory=list)

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


DIRECT_VERIFIED = "DIRECT_VERIFIED"
STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
TRANSFERABLE_PARTIAL = "TRANSFERABLE_PARTIAL"
WEAK_INFERRED = "WEAK_INFERRED"
UNSUPPORTED = "UNSUPPORTED"


@dataclass
class FitEvidence:
    """One requirement ↔ profile evidence link for explainable Candidate Fit."""
    requirement: str
    level: str
    profile_evidence: str = ""


@dataclass
class FitResult:
    """Explainable Candidate Fit breakdown (cf-v2)."""
    overall_fit: Optional[float]
    eligibility: Optional[float] = None
    core_capabilities: Optional[float] = None
    preferred_qualifications: Optional[float] = None
    evidence_confidence: Optional[float] = None
    strong_matches: List[str] = field(default_factory=list)
    partial_matches: List[str] = field(default_factory=list)
    true_gaps: List[str] = field(default_factory=list)
    unknown: List[str] = field(default_factory=list)
    evidence: List[FitEvidence] = field(default_factory=list)
    scoring_version: str = "cf-v2"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_fit": self.overall_fit,
            "eligibility": self.eligibility,
            "core_capabilities": self.core_capabilities,
            "preferred_qualifications": self.preferred_qualifications,
            "evidence_confidence": self.evidence_confidence,
            "strong_matches": list(self.strong_matches),
            "partial_matches": list(self.partial_matches),
            "true_gaps": list(self.true_gaps),
            "unknown": list(self.unknown),
            "evidence": [
                {
                    "requirement": e.requirement,
                    "level": e.level,
                    "profile_evidence": e.profile_evidence,
                }
                for e in self.evidence
            ],
            "scoring_version": self.scoring_version,
        }


class JobQualityStatus(Enum):
    """Posting freshness / URL validity for Step 6 + dashboard filters."""
    ACTIVE = "active"
    STALE = "stale"
    EXPIRED = "expired"
    BROKEN = "broken"
    UNKNOWN = "unknown"


class ProviderRunStatus(Enum):
    """Per-source outcome within a search run."""
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"


class SearchRunStatus(Enum):
    """Aggregate search-run outcome across providers."""
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class ProviderRunResult:
    """One job source's contribution to a search run."""
    source: JobSource
    status: ProviderRunStatus
    scraped: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source.value,
            "status": self.status.value,
            "scraped": self.scraped,
            "error": self.error,
        }


@dataclass
class SearchRunSummary:
    """Observability for a scout run (Step 5) with provider isolation."""
    started_at: datetime
    finished_at: datetime
    providers: List[ProviderRunResult] = field(default_factory=list)
    total_scraped: int = 0
    total_after_dedupe: int = 0
    closed_filtered: int = 0
    total_stored: int = 0
    status: SearchRunStatus = SearchRunStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "providers": [p.to_dict() for p in self.providers],
            "total_scraped": self.total_scraped,
            "total_after_dedupe": self.total_after_dedupe,
            "closed_filtered": self.closed_filtered,
            "total_stored": self.total_stored,
            "status": self.status.value,
        }


@dataclass
class DashboardFilters:
    """Filter + sort criteria for the Job Discovery Dashboard (Step 7)."""
    action: str = "all"
    min_fit: Optional[float] = None
    max_fit: Optional[float] = None
    min_salary: Optional[int] = None
    sponsorship: Optional[str] = None
    work_mode: Optional[str] = None
    source: Optional[str] = None
    quality: Optional[str] = None
    keyword: Optional[str] = None
    sort_by: str = "posted_date"
    sort_dir: str = "desc"
