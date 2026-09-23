"""
Shared section-heading boundary regex used by both the PDF-flattened-text
parser (ResumeParser) and the DOCX structural walker (docx_structure), so
"what counts as the end of a section" is defined once. A prior asymmetry
(the work-experience section boundary not recognizing "ADDITIONAL" while
the summary-extraction boundary already did) let a real resume's trailing
content get silently swallowed into the last job's bullets -- promoting
one shared constant is what keeps that from happening again in a second
place (the DOCX walker) independent of any future edit to this list.
"""

import re

# "EMPLOYMENT" added per a product-revision spec (2026-09-23) listing it as
# a required heading variant alongside "Work Experience"/"Professional
# Experience" -- some resumes use it as the section title instead.
SECTION_BOUNDARY_RE = re.compile(
    r"^\s*(EDUCATION|(?:WORK\s+)?EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT|SKILLS|TECHNICAL|"
    r"CERTIFICATIONS|ADDITIONAL)\b",
    re.IGNORECASE,
)

WORK_EXPERIENCE_HEADING_RE = re.compile(
    r"^\s*(?:WORK\s+)?EXPERIENCE\b|^\s*PROFESSIONAL\s+EXPERIENCE\b|^\s*EMPLOYMENT\b", re.IGNORECASE
)
