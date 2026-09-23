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

SECTION_BOUNDARY_RE = re.compile(
    r"^\s*(EDUCATION|(?:WORK\s+)?EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|SKILLS|TECHNICAL|"
    r"CERTIFICATIONS|ADDITIONAL)\b",
    re.IGNORECASE,
)

WORK_EXPERIENCE_HEADING_RE = re.compile(
    r"^\s*(?:WORK\s+)?EXPERIENCE\b|^\s*PROFESSIONAL\s+EXPERIENCE\b", re.IGNORECASE
)
