# Spec 001: Job Application Copilot — Full Product Vision

**Status:** Draft
**Date:** 2026-09-16

## Problem

Job seekers spend enormous amounts of time on repetitive tasks: searching multiple job boards,
manually checking whether their resume matches each job's ATS keyword requirements, and
tailoring their resume for every single application. About 95% of employers use ATS systems to
filter applications by keyword match, so a resume that isn't tailored to each job description
often never reaches a human. I've experienced this myself and seen my peers go through the same
slow, repetitive process while job hunting.

## What we're making

A tool that takes a user's resume and job goals, and automates the repetitive parts of the job
search and application process while keeping the user in control of every decision. The full
workflow:

1. **Upload Resume** — user uploads PDF/DOCX; system extracts contact info, education, work
   experience, accomplishments, skills, tools, certifications. Original resume is preserved and
   never overwritten.

2. **Build the Career Truth Profile** — convert the resume into structured, verified data that
   becomes the only source of truth the AI can draw from when tailoring resumes. The system may
   rephrase, reorganize, shorten, strengthen wording, or highlight existing experience
   differently. It may never invent experience, skills, certifications, numbers, responsibilities,
   or change factual dates/employers.

3. **Set Job Search Goals** — role/title, industry, experience level, location, salary,
   company type, target companies, companies to exclude, work authorization/sponsorship needs,
   full-time/internship, remote preference, travel tolerance, relocation willingness.

4. **Select Job Sources** — user chooses which platforms to search (LinkedIn, Indeed, Handshake,
   Monster, Greenhouse, Lever, Ashby, Workday, company career pages).

5. **Scout Open Jobs** — search selected sources using the user's goals; collect company, title,
   location, work mode, description, salary range, dates, employment type, experience/education
   required, sponsorship info, company size, industry, ATS platform, source link.

6. **Clean and Validate Job Results** — deduplicate the same job across multiple sources
   (prefer the employer's original page), validate the posting is still open and the URL works.
   When information is unavailable, show "Unknown" rather than guessing.

7. **Show the Job Discovery Dashboard** — searchable/filterable table of jobs with fit score,
   salary, sponsorship, posted date, deadline, and application status.

8. **Calculate Candidate-to-Job Fit** — compare the verified Career Truth Profile against each
   job's requirements to produce a **Candidate Fit Score**: how well the person's actual
   background matches the job (separate from how well their resume currently communicates it).

9. **User Selects Jobs** — the system never auto-applies to everything it finds. Users mark jobs
   Interested, Save for Later, Skip, or Apply. Only "Apply" jobs proceed to tailoring.

10. **Analyze the Job Description** — break it into required/preferred qualifications,
    responsibilities, technical/soft skills, tools, terminology, education, experience, and
    weighted keywords (high/medium/low importance).

11. **Benchmark the Original Resume** — produce a **Resume Match Score**, distinct from
    Candidate Fit. A candidate can be 90% qualified but only 67% represented on their current
    resume.

12. **Create the Resume Gap Report** — classify every requirement into: (A) already on resume,
    (B) supported by experience but missing from resume, (C) can be rephrased to match JD
    language, (D) needs user confirmation (system isn't sure), (E) truly missing — never added.

13. **Tailor the Resume** — rephrase, rearrange, reprioritize, and strengthen wording using only
    verified experience. Never fabricate.

14. **Optimize Toward the Target Match** — loop analyze → rewrite → score → improve until the
    resume reaches ≥85% alignment or no truthful improvement remains (report the ceiling and
    what's still missing rather than fabricate to close the gap).

15. **Control Resume Length** — user chooses 1 page, 2 pages, or preserve original length;
    system adjusts bullet count/length, spacing, and content priority accordingly.

16. **Preserve Resume Design** — keep the tailored resume as close as practical to the original's
    section order, fonts, formatting, and layout. Output must be clean, professional,
    ATS-readable, and text-based (never an image).

17. **Generate PDF** — produce the job-specific PDF (e.g.
    `Shangjun_Yang_CVS_Strategy_Manager.pdf`) and preserve an editable version where possible.

18. **PDF Quality Verification (hard gate)** — reopen the generated PDF, extract its text, and
    verify: contact info detected, employer/title/dates/accomplishments detected, correct page
    count, no overlapping/clipped/missing/broken text, sensible reading order, text
    selectable/extractable, standard section headings detectable. If validation fails, regenerate
    — never ship a broken PDF.

19. **Final Application Report** — show Candidate Fit, Original Resume Match, Tailored Resume
    Match, qualifications represented, missing qualifications, unsupported claims added (should
    always be 0), PDF validation result, ATS readability result, and resume length.

20. **Show Resume Changes** — side-by-side original vs. tailored bullets with the reasoning for
    each change, so the user can review before applying.

21. **Choose Application Mode** — every application offers three modes:
    - **Manual:** system generates the resume and provides the link; user applies themselves.
    - **Assist:** system fills in known fields (contact, education, employment, resume upload,
      previously approved answers) and drafts answers to custom questions, then **stops before
      submit** for user review.
    - **Auto:** for supported ATS platforms, system completes and submits the application, but
      always stops and asks the user when it hits unknown questions, unverified answers,
      CAPTCHA, login verification, or conflicting/sensitive information. Never guess.

22. **Record Exactly What Was Submitted** — company, position, job URL/description, application
    date/source, resume version used, both fit/match scores, answers given, application mode,
    and confirmation number — a full audit trail.

23. **Update Application Status** — track each job through Discovered → Interested → Preparing →
    Ready to Apply → Applied → Recruiter Screen → Interview → Final Interview → Offer/
    Rejected/Withdrawn.

24. **Application Dashboard** — a single command-center view of every job: fit, resume match,
    status, date applied, and resume used.

The non-negotiable rule across every step: **optimize presentation, never manufacture
qualifications.**

## Out of scope (phased across sprints)

This spec describes the full multi-sprint product. It is not one deliverable. Phasing:

- **Sprint 1 (steps 1, 2, 10–20):** Career Truth Profile, job-description analysis, resume
  benchmarking, gap report, truthful tailoring loop to ≥85% alignment, length control, PDF
  generation with hard validation gate, and the final report showing resume changes. No job
  search, no auto-apply. Interface is a basic web form (single resume + single job description
  in, tailored PDF + report out).

- **Sprint 2 (steps 3–9):** job search goals, source selection, scouting across job boards,
  deduplication/validation, Candidate Fit scoring, job discovery dashboard, and user
  triage (Interested/Save/Skip/Apply).

- **Sprint 3+ (steps 21–24):** Manual/Assist/Auto application modes, form-filling and
  submission, full audit trail, and the ongoing application-status dashboard.

## Definition of done

- [ ] Sprint 1: a working MVP where a user can upload a resume and a job description, see a gap
      report, receive a tailored one-page PDF that reaches ≥80% keyword/qualification alignment
      on 8 of 10 real job postings tested, and confirm the PDF passes the round-trip text
      validation.
- [ ] Sprint 1: at least 3 job seekers other than me can use the tool to generate a tailored
      resume without my help.
- [ ] Sprint 2: the job discovery dashboard returns real, deduplicated job listings from at
      least one job source, filtered by the user's stated goals.
- [ ] Sprint 3+: at least one supported ATS platform can be filled in Assist mode and reviewed
      by the user before submission.
