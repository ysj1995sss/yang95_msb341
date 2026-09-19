# Resume Tailoring MVP — Architecture

## Pipeline Overview

The Resume Tailoring MVP is a single-user web application that orchestrates a nine-stage pipeline to take a resume and job description as input and produce a tailored, keyword-optimized PDF resume as output. The pipeline is linear and synchronous, with each stage feeding its output to the next.

```
Upload Resume + Job Description
        ↓
Resume Parser (extract contact, education, experience, skills, tools, certifications)
        ↓
Career Truth Profile (structured, verified source of truth)
        ↓
Job Analyzer (break down requirements, qualifications, skills, tools)
        ↓
Resume Benchmarker (score how well current resume communicates capabilities)
        ↓
Gap Analyzer (classify each requirement A–E)
        ↓
Resume Tailorer + Optimization Loop (Claude-powered, iteratively improve until ≥85% alignment)
        ↓
PDF Generator (produce polished, one-page resume)
        ↓
PDF Validator (hard gate: round-trip text extraction, verify ATS readability)
        ↓
Report Generator (final summary: fit, match scores, gap classifications, validation)
        ↓
User receives tailored PDF + report
```

All orchestration happens in `resume_tailorer/app.py` (Streamlit). No stage modifies the CareerTruthProfile; all tailoring is derived from it and validated against it.

## Module Responsibilities

### `models/` — Data Models and Single Source of Truth

Defines the **Career Truth Profile** and supporting data structures. The CareerTruthProfile is the *only* source of truth from which tailoring decisions draw. It is immutable and never altered after creation.

**Key classes:**
- `CareerTruthProfile` — immutable record of contact info, education, work experience, skills, tools, certifications, and career-level accomplishments.
- `WorkExperience` — employer, title, dates, responsibilities, and accomplishments (measured outcomes).
- `EducationEntry` — degree, field, institution, year, GPA.

**Constraint:** The Career Truth Profile contains only what is extractable or inferrable from the original resume. It never adds or fabricates content.

### `parsers/` — Resume Parsing and Extraction

Converts unstructured resume text (from PDF or DOCX) into a structured CareerTruthProfile.

**Key class:**
- `ResumeParser` — reads PDF/DOCX files, extracts text, and parses it into a CareerTruthProfile using pattern matching and simple heuristics.

**How it works:**
1. Extract text from PDF (via pypdf) or DOCX (via python-docx).
2. Use regular expressions and keyword matching to identify sections (education, work experience, skills, etc.).
3. Parse each section into the corresponding data structures.
4. Return a complete CareerTruthProfile.

**Constraint:** Never invent or assume information not explicitly present in the resume.

### `analyzers/` — Job Analysis, Resume Scoring, and Gap Classification

Three separate analyzers that work together to understand the job, score the current resume, and classify gaps.

**Key classes:**

#### `job_analyzer.py` — Job Description Analysis
- `JobAnalyzer` — parses job description text into structured data.
- `JobAnalysis` — breakdown including required/preferred qualifications, responsibilities, technical/soft skills, tools, education level, experience level, and weighted keywords (high/medium/low importance).

**How it works:**
1. Extract key sections from the job description text (responsibilities, required qualifications, preferred qualifications).
2. Identify technical skills, tools, certifications, education, and experience requirements.
3. Weight keywords by frequency and position in the job description.
4. Return a complete JobAnalysis object.

**Constraint:** Extract what the job *actually* asks for, not what we assume job titles require.

#### `resume_benchmarker.py` — Resume Match Scoring
- `ResumeBenchmarker` — scores how well the *current* (untailored) resume communicates the candidate's capabilities.
- `ResumeBenchmark` — result object including match score, covered skills, covered tools, covered qualifications, and missing items.

**How it works:**
1. Compare the resume's stated skills, tools, and accomplishments against the job's stated requirements.
2. Score alignment on a 0.0–1.0 scale for keywords and qualifications separately.
3. Identify which requirements are already present in the resume and which are absent.
4. Return a ResumeBenchmark with the original score and details.

**Constraint:** Score the resume as-is, without any interpretation or assumption.

#### `gap_analyzer.py` — Gap Classification (A–E)
- `GapAnalyzer` — classifies each job requirement into one of five categories.
- `GapCategory` enum and `GapReport` — structured gap report.

**Gap Categories:**
- **A (Already on resume)** — the requirement is explicitly stated in the current resume.
- **B (Supported but missing)** — the candidate has demonstrable experience supporting this requirement (e.g., managed databases) but the resume doesn't use the specific keyword (e.g., "SQL").
- **C (Rephrasable)** — the current resume wording can be adjusted to match the job description's language without altering the facts.
- **D (Needs confirmation)** — the system isn't certain whether the requirement is supported; it requires human review.
- **E (Truly missing)** — the candidate genuinely lacks this capability; it will never be added to the resume.

**How it works:**
1. For each requirement from the job analysis, search the resume for exact or semantic matches.
2. If found, mark as **A**.
3. If not found but the Career Truth Profile contains related experience, mark as **B** with evidence.
4. If found but worded differently, mark as **C** with the current wording.
5. If uncertain, mark as **D** with the reason for uncertainty.
6. If genuinely absent from the Career Truth Profile, mark as **E**.

**Constraint:** Never classify as anything other than **E** if the candidate's verified experience does not support the requirement.

### `tailorer/` — Resume Tailoring and Optimization

Two-part system: the Resume Tailorer performs a single pass of Claude-powered tailoring, and the Optimizer loops until ≥85% alignment is reached (or the truthful ceiling is hit).

**Key classes:**

#### `resume_tailorer.py` — Claude-Powered Tailoring (Single Pass)
- `ResumeTailorer` — calls Claude API with strict safety prompts to rephrase and reorder existing resume content.
- `TailoredResume` — output including tailored bullets, explanations for each change, and a mapping back to the original.

**How it works:**
1. Build a Claude prompt that includes:
   - The Career Truth Profile (immutable).
   - The original resume text.
   - The job description.
   - Gap classifications (what's missing, what's hidden, what's rephrasable).
   - **Strict safety prompt:** "Optimize presentation of existing experience only. Never fabricate, invent, or assume capabilities not in the Career Truth Profile. Never add false claims."
2. Call Claude to generate tailored bullets that better match the job language.
3. For each tailored bullet, include an explanation of why it was changed.
4. Return a TailoredResume object with old and new bullets side-by-side.

**Constraint:** Every tailored bullet is auditable back to the Career Truth Profile. The system prompt is versioned and logged.

#### `optimizer.py` — Optimization Loop
- `ResumeTailoringOptimizer` — runs multiple iterations of tailor → score → compare until convergence.
- `OptimizationResult` — final tailored resume, iteration count, final score, and whether target was reached.

**How it works:**
1. Start with the original resume and initial score from ResumeBenchmarker.
2. Call ResumeTailorer to produce a tailored version.
3. Score the tailored resume.
4. If score ≥ 85%, return success.
5. If score improved, increment iteration counter and repeat from step 2.
6. If score did not improve or max iterations reached, return the best version found and report the ceiling.

**Constraint:** Never fabricate to improve score; if the ceiling is hit, report it honestly.

### `pdf/` — PDF Generation and Round-Trip Validation

Two-part system: the Generator produces the PDF, and the Validator ensures it is text-based and ATS-readable.

**Key classes:**

#### `generator.py` — PDF Generation
- `PDFGenerator` — converts a tailored resume into a polished, one-page PDF.
- `GeneratedPDF` — output including file path and page count.

**How it works:**
1. Take the tailored resume text and structure.
2. Preserve the original resume's section order, fonts, and formatting as much as possible.
3. Adjust spacing, margin, and bullet length to fit one page.
4. Generate a text-based (not image-based) PDF using reportlab.
5. Return the file path and page count.

**Constraint:** Output must be text-based and ATS-readable; never output an image or unsearchable PDF.

#### `validator.py` — PDF Validation (Hard Gate)
- `PDFValidator` — round-trip validation: reopen the PDF, extract its text, and verify it is not broken.
- `ValidationResult` — passed/failed, page count, extracted text, and issues list.

**How it works:**
1. Open the generated PDF file.
2. Extract text back out (round-trip).
3. Check:
   - Text is not empty (confirms it's not image-based).
   - Page count is reasonable (≤2 for MVP).
   - Extracted text is not dominated by garbage/control characters (confirms it's not corrupted).
4. Return a ValidationResult with `passed=True/False` and details.

**Hard Gate:** If validation fails, the caller (app.py) must regenerate the PDF before shipping it to the user. A broken PDF never reaches the user.

### `utils/` — Utility Functions

Scoring and helper functions.

**Key module:**
- `scoring.py` — keyword_alignment_score() and qualification_alignment_score() functions that compare resume text against job requirements on a 0.0–1.0 scale.

### `report_generator.py` — Final Application Report

Assembles all intermediate results into a single final report for the user.

**Key class:**
- `ReportGenerator` — produces a structured report including:
  - Original resume match score
  - Tailored resume match score
  - Gap classifications (A/B/C/D/E counts)
  - Candidate Fit vs. Resume Match distinction
  - PDF validation result
  - Resume length (1-page vs. original)

## Safety Architecture

The Resume Tailoring MVP enforces safety through **constraint-based design** rather than post-hoc filtering:

### 1. Career Truth Profile — Single Source of Truth
- All tailoring draws *only* from the CareerTruthProfile.
- The profile is created once, never modified, and never bypassed.
- Every tailored claim is traceable back to a fact in the profile.

### 2. System Prompt Guardrails (Claude API)
- When calling Claude for resume tailoring, the system prompt includes explicit constraints:
  - "Optimize presentation of existing experience only."
  - "Never fabricate, invent, or assume capabilities not in the Career Truth Profile."
  - "Never add false claims, false dates, false employers, or false certifications."
  - "Rephrase, reorganize, and strengthen; never invent."
- The system prompt is versioned and logged with every API call so changes can be audited.

### 3. Gap Classification as Guardrail
- The GapAnalyzer explicitly classifies each requirement as A–E.
- Category **E (Truly missing)** is never tailored into the resume.
- The gap report is shown to the user so they understand what's truthfully absent.

### 4. Round-Trip PDF Validation (Hard Gate)
- After PDF generation, the validator immediately re-opens the PDF and extracts its text.
- If the round-trip fails (text is corrupted, empty, or unreadable), the PDF is regenerated or rejected.
- A broken PDF never reaches the user.

### 5. Audit Trail
- Every tailoring decision is logged with:
  - Original bullet.
  - Tailored bullet.
  - Reason for change (from Claude explanation).
  - Match scores before and after.
  - Whether the change was within the Career Truth Profile bounds.

## Gap Classification (A–E) Reference

When a user runs the tailoring pipeline, the Gap Report shows which requirements are already supported, which are hidden, which are rephrasable, and which are truly missing:

| Category | Meaning | Tailoring Action |
|----------|---------|------------------|
| **A** | Already on resume | Possibly rephrase to match job language (Category C) |
| **B** | Supported by experience but missing from resume | Add to resume if supported; verify with user |
| **C** | Rephrasable | Reword to match job language |
| **D** | Needs confirmation | Flag for user review; do not auto-tailor |
| **E** | Truly missing | Never add; report as absent and calculate as 0% support |

The gap report is always shown to the user before they apply, so they understand what's missing and what would require fabrication.

## Current Scope (Sprint 1)

This MVP covers steps 1–2 and steps 10–20 of the full Job Application Copilot spec:
- Resume parsing and Career Truth Profile extraction
- Job description analysis
- Resume benchmarking and gap classification
- Resume tailoring and optimization with strict safety guardrails
- PDF generation and validation
- Final report generation

It does **not** cover:
- Job search and job discovery (Sprint 2)
- Candidate Fit Score (Sprint 2)
- Auto-apply or form-filling (Sprint 3+)
- Multi-job application tracking (Sprint 3+)

## Future Sprints

### Sprint 2 — Job Search and Discovery
- Add job search goals configuration (title, industry, location, salary, sponsorship, etc.)
- Scout jobs across multiple job boards (LinkedIn, Indeed, Handshake, etc.)
- Deduplication and validation of job listings
- Calculate **Candidate Fit Score** (how qualified the candidate actually is, separate from resume match)
- Display a searchable/filterable job discovery dashboard
- Allow user to triage jobs (Interested, Save, Skip, Apply)

### Sprint 3+ — Auto-Apply and Application Tracking
- Implement three application modes: Manual, Assist, Auto
- Form-filling and submission for supported ATS platforms
- Full audit trail (what was submitted, when, what resume version was used)
- Application status tracking (Discovered → Applied → Interview → Offer/Rejected)

## Testing

The test suite includes 323 tests covering:
- Resume parsing (PDF and DOCX)
- Career Truth Profile construction
- Job analysis
- Resume benchmarking and scoring
- Gap classification (A–E)
- Resume tailoring (Claude safety guardrails)
- Optimization loop (convergence, iteration count)
- PDF generation and validation (round-trip text extraction)
- Report generation
- Integration tests against real job postings

Run with:
```bash
cd product
pytest tests/ -v
```

For details on test structure and how to add new tests, see the test files directly.

## Architecture Diagrams

### Data Flow
```
Resume File (PDF/DOCX)
    ↓
ResumeParser → CareerTruthProfile (immutable)
    ↓
ResumeBenchmarker → ResumeBenchmark (original score)
    ↓
GapAnalyzer → GapReport (A-E classification)
    ↓
ResumeTailorer (Claude API, safety prompts)
    ↓
TailoredResume
    ↓
PDFGenerator → PDF File
    ↓
PDFValidator → ValidationResult (hard gate)
    ↓
ReportGenerator → Final Report + PDF to User
```

### Safety Constraints
```
CareerTruthProfile
    ↓
    └─→ ResumeTailorer (reads only)
            ↓
            └─→ System Prompt (guardrails)
                    ↓
                    └─→ Claude API
                            ↓
                            └─→ TailoredResume (auditable to profile)
```

### Optimization Loop
```
Original Resume
    ↓
ResumeTailorer (pass 1) → TailoredResume₁
    ↓
Score → 65%
    ↓
ResumeTailorer (pass 2) → TailoredResume₂
    ↓
Score → 78%
    ↓
ResumeTailorer (pass 3) → TailoredResume₃
    ↓
Score → 85% (target reached)
    ↓
Output TailoredResume₃
```

If the score plateaus before reaching 85%, the optimizer reports the ceiling and outputs the best version found.

## Configuration and Secrets

Resume tailoring uses a provider-agnostic LLM client (`LLMClient` / LiteLLM). Required settings:

- `LLM_MODEL` — LiteLLM model id (e.g. `openai/gpt-4o`, `anthropic/claude-3-5-sonnet-20241022`)
- `LLM_API_KEY` — API key for that provider
- `LLM_API_BASE` — optional base URL for proxies or compatible endpoints

They can be loaded from:
1. Shell environment variables (e.g. `set LLM_MODEL=...` / `export LLM_MODEL=...`)
2. `.env` file (via python-dotenv)
3. Streamlit sidebar **Model provider** section (session-only overrides; keys are not persisted)
4. Deployment environment (e.g., Streamlit Cloud secrets)

Job Search and Applications do not require LLM settings. Missing model/key fails hard with a clear error — there is no silent Anthropic default. Migration: former `ANTHROPIC_API_KEY`-only setups should set `LLM_MODEL=anthropic/...` and `LLM_API_KEY`.

Do not commit API keys to version control.

## Deployment Notes

The MVP is a single-user Streamlit web application. To deploy:
1. Host on Streamlit Cloud, Heroku, or a self-managed server.
2. Ensure Python 3.11+ is available.
3. Install requirements: `pip install -r requirements.txt`
4. Set `LLM_MODEL` and `LLM_API_KEY` (and optionally `LLM_API_BASE`) in the deployment environment.
5. Run: `streamlit run resume_tailorer/app.py`

For multi-user deployment, consider:
- Session-based storage for user resumes (currently stored in tempfiles)
- Database for storing tailoring history and optimization results
- Async job queue for long-running PDF generation and validation
- Rate limiting on LLM provider calls (currently unbounded in the MVP)
