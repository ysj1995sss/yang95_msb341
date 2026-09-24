from pydantic import BaseModel, Field

TargetLength = str  # "1_page" | "2_page" | "preserve"


class TailorRequest(BaseModel):
    """Either job_description or job_id (a captured Job to pull the description from)."""

    job_description: str = ""
    job_id: str | None = None
    generate_pdf: bool = False
    # Base rule: match the length of whatever resume the user actually
    # uploaded, rather than always defaulting to a fixed 1-page target
    # regardless of how long their real resume is. "preserve" detects the
    # original's real page count (see ResumeParser._detect_pdf_style) and
    # targets that -- falling back to a middle-ground preset only if no
    # original file was uploaded to detect a page count from.
    target_length: TargetLength = "preserve"
    # When True, restrict tailoring to inserting missing ATS keywords into
    # existing bullets rather than a full rewrite -- for a user who wants
    # their resume's wording and structure left otherwise untouched.
    conservative: bool = False


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
    # Populated instead of a from-scratch pdf_base64 when the original
    # upload was a .docx: the ORIGINAL document with tailored bullet text
    # spliced into its own paragraphs (see resume_tailorer.docx_export).
    # pdf_base64 is still populated alongside this too when generate_pdf is
    # true and Word conversion succeeds -- docx_base64 is always the
    # machine-editable artifact, pdf_base64 is always "a human-readable
    # file, if one could be produced."
    docx_base64: str | None = None
    original_page_count: int | None = None
    tailored_page_count: int | None = None
    page_count_preserved: bool | None = None
    # None when the original wasn't a DOCX at all (this field is only
    # meaningful on the DOCX path); False means DOCX conversion was
    # attempted but Word/docx2pdf wasn't available or failed.
    docx_conversion_available: bool | None = None
    bullet_warnings: list[str] = Field(default_factory=list)
    # Only meaningful on the DOCX path (0 otherwise) -- a self-check on
    # tailoring quality, not just formatting: how many bullets were
    # evaluated/changed/rejected by a code-level guardrail, how many job
    # requirements had real resume evidence, and whether the pass looks
    # suspiciously shallow given that evidence count.
    bullets_evaluated: int = 0
    bullets_changed: int = 0
    bullets_rejected: int = 0
    addressable_requirements: int = 0
    tailoring_seems_shallow: bool = False
