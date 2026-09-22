from pydantic import BaseModel, Field

TargetLength = str  # "1_page" | "2_page" | "preserve"


class TailorRequest(BaseModel):
    """Either job_description or job_id (a captured Job to pull the description from)."""

    job_description: str = ""
    job_id: str | None = None
    generate_pdf: bool = False
    target_length: TargetLength = "1_page"


class GapItemOut(BaseModel):
    requirement: str
    category: str
    reason: str
    evidence: str = ""


class BulletChangeOut(BaseModel):
    original: str
    tailored: str
    change_type: str
    reasoning: str


class TailorResult(BaseModel):
    # Spec 001 item 19 ("Final Application Report"): Candidate Fit (how well
    # the person's actual background matches the job) is distinct from
    # Resume Match (how well the CURRENT resume communicates it). None when
    # there isn't enough job data to score fit honestly.
    candidate_fit_score: float | None = None
    original_match_score: float
    tailored_resume: str
    final_score: float
    iterations: int
    ceiling_reached: bool
    missing_qualifications: list[str] = Field(default_factory=list)
    gap_summary: str
    gaps: list[GapItemOut] = Field(default_factory=list)
    changes: list[BulletChangeOut] = Field(default_factory=list)
    fabrication_risk_issues: list[str] = Field(default_factory=list)
    # Spec 001 item 19: "unsupported claims added (should always be 0)".
    unsupported_claims_added: list[str] = Field(default_factory=list)
    pdf_base64: str | None = None
    pdf_issues: list[str] = Field(default_factory=list)
