# Steps 16-20 validated-artifact acceptance fixtures

Both resumes below are entirely fictitious -- no real names, contact
details, employers, or personal history. They were generated
specifically for this test suite (see the generation notes at the
bottom) rather than adapted from any real person's resume.

## `sample_docx_resume.docx`

Candidate "Alex Rivera," a backend software engineer with two jobs, one
degree, and multiple quantified bullets (`35%`, `60%`, `2 million daily
requests`, `10x user growth`). Exercises the **DOCX splice path**
(`run_docx_tailoring_pipeline`): the docx structural walker must find
both job anchors, both bullet lists, the education line, and the
contact header, and the splice must leave every non-tailored paragraph
byte-for-byte untouched.

Paired in tests with `JOB_DESCRIPTIONS[0]` from
`product/tests/fixtures/real_job_descriptions.py` (a backend software
engineer posting) -- its required skills (Python, REST APIs, Docker,
PostgreSQL, Kubernetes, AWS) deliberately overlap with this resume's
`SKILLS` line so the gap analyzer finds real, addressable requirements
to tailor toward.

## `sample_pdf_only_resume.pdf`

Candidate "Jordan Lee," a data analyst with two jobs, one degree, and
quantified bullets (`22%`, `10 hours per week`, `30+ stakeholders`).
Built directly with a plain `reportlab` canvas (literal `-` bullet
characters, no special glyphs) rather than through this codebase's own
`PDFGenerator` -- `PDFGenerator` renders bullets as a symbol-font glyph
meant for a *tailored output* artifact, which the parser's bullet
detection (looking for a literal `-`/`•` in extracted text) can't
recover from. A plain-text PDF export is what a real "PDF-only original
upload" actually looks like, and is what exercises the **freeform
reconstruction path** honestly.

Paired in tests with `JOB_DESCRIPTIONS[1]` (a senior data scientist
posting) -- the closest data-oriented posting in the existing fixture
set.

## Known limitation: no scraped real-world job posting

Both job descriptions are the same synthetic-but-realistic fixtures
`product/tests/fixtures/real_job_descriptions.py` already uses and
documents ("Actual scraped job postings were not accessible in this
environment") -- that constraint was still true for this task, and
reusing an already-reviewed fixture avoided introducing a new,
un-vetted, possibly copyrighted job posting snapshot into the repo.

## Regenerating these fixtures

There is no committed generator script (keeping the fixture set to
exactly the files the sprint plan lists). Both files were produced by a
one-off script built from `product/tests/test_docx_pipeline.py`'s
`_sample_docx_bytes` helper (for the DOCX bullet/numbering XML) and a
plain `reportlab.pdfgen.canvas.Canvas` (for the PDF) using the resume
text quoted in `product/tests/test_artifact_acceptance.py`.
