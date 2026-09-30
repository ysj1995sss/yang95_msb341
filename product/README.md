# Resume Tailoring MVP

A web-based resume tailoring assistant that uploads a resume and job description, produces a comprehensive gap analysis, and generates a tailored PDF resume with ≥80% keyword alignment—all while maintaining complete honesty about the candidate's qualifications.

## Core Principle

**Optimize presentation, never manufacture qualifications.**

The Resume Tailoring MVP enforces a strict safety architecture: the **Career Truth Profile** (a structured, verified extract of the candidate's resume) is the *only* source of truth. The system never fabricates experience, skills, certifications, dates, employers, or accomplishments. It rephrase, reorganizes, reorders, and strengthens *existing* experience to better communicate what is already true. Every tailoring decision is auditable and constrained by the original resume content.

## Project Overview

This is **Sprint 1** of a larger Job Application Copilot. The MVP orchestrates this pipeline:

1. **Resume Parser** — extracts contact info, education, work experience, accomplishments, skills, tools, and certifications into a structured Career Truth Profile.
2. **Job Analyzer** — breaks down the job description into required/preferred qualifications, responsibilities, technical/soft skills, tools, and weighted keywords.
3. **Resume Benchmarker** — scores how well the *current* resume communicates the candidate's capabilities (distinct from how qualified they actually are).
4. **Gap Analyzer** — classifies every job requirement into categories A–E to identify what's missing, what's hidden, and what's truly absent.
5. **Resume Tailorer** — rephrases, reorders, and strengthens existing experience using Claude's language model (with strict safety prompts that prevent fabrication).
6. **Optimization Loop** — iteratively refines the tailored resume, re-scoring it at each step to reach ≥85% alignment or report the truthful ceiling.
7. **PDF Generator** — produces a polished, one-page PDF with clean formatting and ATS-readable structure.
8. **PDF Validator** — round-trip validation: re-opens the PDF, extracts its text, and verifies it is not image-based, not corrupted, and text-extractable (a *hard gate* that prevents shipping broken PDFs).
9. **Report Generator** — produces a final application report showing candidate fit, original resume match, tailored resume match, gap classifications, and validation results.

The system targets **80%+ keyword/qualification alignment** on real job postings while preserving the candidate's resume design and maintaining truthfulness above all.

## Installation

### Requirements
- Python 3.11 or higher
- pip (Python package manager)

### Setup

```bash
# Clone or navigate to the product directory
cd product

# Install dependencies
pip install -r requirements.txt
```

The `requirements.txt` includes:
- **streamlit** — web UI framework
- **litellm** — multi-provider LLM client for resume tailoring
- **pypdf** — PDF reading and validation
- **python-docx** — DOCX resume parsing
- **reportlab** — PDF generation
- **pytest** — testing framework
- **python-dotenv** — environment variable management

## Configuration

### Required Environment Variables (or use the sidebar)

```bash
set LLM_MODEL=openai/gpt-4o
set LLM_API_KEY=sk-...
# optional
set LLM_API_BASE=https://your-proxy.example/v1
```

In the Streamlit sidebar, section **Model provider** overrides these when filled.
Job Search and Applications do not need an LLM key.

Migration from Anthropic-only setup: use `LLM_MODEL=anthropic/claude-3-5-sonnet-20241022` and set `LLM_API_KEY` to your Anthropic key (do not rely on `ANTHROPIC_API_KEY` alone).

Set these in your shell, in a `.env` file (loaded via `python-dotenv`), or in your deployment environment.

### Sign-in and where data is stored

- `JOB_COPILOT_DATA_DIR`: the folder for each user's jobs, applications and tailored files
  (default `~/.job_copilot`). Use a durable disk in any hosted deployment.
- `[auth]` in Streamlit secrets: turns on Google sign-in, so each person gets a private
  workspace. Without it the app runs in local single-user mode and warns not to share the
  link. See `decisions/023` for the full deployment checklist.
- `JOB_COPILOT_API_BASE`: the profile API address used by Fact Vault (default
  `http://localhost:8000`).

## Usage

### Launch the Web UI

```bash
streamlit run resume_tailorer/app.py
```

The Streamlit app opens in your browser at `http://localhost:8501`. Configure the model in the sidebar (or via env), upload a resume (PDF or DOCX), paste a job description, and click "Tailor my resume" to receive a gap analysis, tailored resume PDF, and final report.

### Input

1. **Resume** — PDF or DOCX file containing your work experience, education, skills, tools, and accomplishments.
2. **Job Description** — text from a job posting describing the role, requirements, responsibilities, and preferred qualifications.

### Output

1. **Career Truth Profile** — structured data extracted from your resume (education, work experience, skills, tools, certifications).
2. **Job Analysis** — breakdown of the job description into required/preferred qualifications, responsibilities, skills, and tools.
3. **Gap Report** — A–E classification of every requirement (already on resume, supported but hidden, rephrasable, needs confirmation, truly missing).
4. **Tailored Resume** — one-page PDF optimized for keyword alignment, preserving your original resume structure and design as much as possible.
5. **Validation Report** — confirmation that the PDF is text-based, not corrupted, and ATS-readable.
6. **Final Report** — summary showing original resume match, tailored resume match, qualifications represented, missing qualifications, resume length, and validation status.

## Running Tests

The project includes **786 tests** (plus 70 in `apps/api/`), run in CI on every push, covering:
- Resume parsing from PDF and DOCX formats
- Career Truth Profile construction
- Job description analysis
- Resume benchmarking and gap classification
- Resume tailoring and optimization
- PDF generation, validation, and round-trip text extraction
- Report generation
- Keyword and qualification alignment scoring

```bash
# Run all tests with verbose output
cd product
pytest tests/ -v

# Run tests for a specific module
pytest tests/test_resume_parser.py -v

# Run tests matching a pattern
pytest -k "test_gap_analyzer" -v
```

## Project Structure

```
product/
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── run_tests.py                     # Test runner script
└── resume_tailorer/                 # Main package
    ├── __init__.py
    ├── app.py                       # Streamlit web UI (orchestration layer)
    ├── models/                      # Data models
    │   ├── career_profile.py        # CareerTruthProfile, WorkExperience, EducationEntry
    │   └── __init__.py
    ├── parsers/                     # Resume parsing
    │   ├── resume_parser.py         # Extracts resume text → CareerTruthProfile
    │   └── __init__.py
    ├── analyzers/                   # Job and resume analysis
    │   ├── job_analyzer.py          # Breaks down job description
    │   ├── resume_benchmarker.py    # Scores resume match
    │   ├── gap_analyzer.py          # Classifies gaps A–E
    │   └── __init__.py
    ├── tailorer/                    # Resume tailoring and optimization
    │   ├── resume_tailorer.py       # Claude-powered tailoring (with safety guardrails)
    │   ├── optimizer.py             # Optimization loop (iterate → score → improve)
    │   └── __init__.py
    ├── pdf/                         # PDF generation and validation
    │   ├── generator.py             # Generates tailored resume PDF
    │   ├── validator.py             # Hard-gate validation (round-trip text extraction)
    │   └── __init__.py
    ├── utils/                       # Utilities
    │   ├── scoring.py               # Keyword and qualification alignment scoring
    │   └── __init__.py
    ├── report_generator.py          # Generates final application report
    ├── docs/                        # Documentation (see docs/architecture.md)
    │   └── architecture.md
    └── tests/                       # Test suite (786 tests)
        ├── __init__.py
        ├── test_resume_parser.py
        ├── test_job_analyzer.py
        ├── test_resume_benchmarker.py
        ├── test_gap_analyzer.py
        ├── test_resume_tailorer.py
        ├── test_optimizer.py
        ├── test_pdf_generator.py
        ├── test_pdf_validator.py
        ├── test_report_generator.py
        ├── test_career_profile.py
        ├── test_scoring.py
        ├── test_integration.py
        └── fixtures/
            └── real_job_descriptions.py
```

### Key Modules

- **models/** — Data structures (CareerTruthProfile, WorkExperience, EducationEntry) that form the single source of truth.
- **parsers/** — Resume text extraction and parsing from PDF/DOCX into a Career Truth Profile.
- **analyzers/** — Job description analysis, resume benchmarking, and gap classification (A–E categories).
- **tailorer/** — Claude-powered resume tailoring with strict safety guardrails to prevent fabrication; optimization loop to reach ≥85% alignment.
- **pdf/** — PDF generation with formatting preservation and round-trip validation to ensure ATS readability.
- **utils/** — Scoring algorithms for keyword and qualification alignment.
- **tests/** — Comprehensive test coverage including integration tests against real job postings.

## Architecture

For a detailed explanation of the pipeline, module responsibilities, safety architecture, and gap classification system, see [docs/architecture.md](docs/architecture.md).

## Limitations and Future Work

This is **Sprint 1** of the Job Application Copilot MVP. Future sprints will add:

- **Sprint 2** — Job search and discovery: set job search goals, scout jobs across multiple job boards, deduplicate listings, calculate Candidate Fit Score, and display a filterable job discovery dashboard.
- **Sprint 3+** — Auto-apply: manual, assisted, and automated application modes for supported ATS platforms, with full audit trail and application status tracking.

See [../specs/001-job-application-copilot.md](../specs/001-job-application-copilot.md) for the full product vision.

## Support

For questions or issues, refer to the test suite in `tests/` and the docstrings throughout the codebase. Each module is documented with its responsibilities and constraints.
