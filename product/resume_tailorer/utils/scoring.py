"""
Scoring utilities for calculating keyword and qualification alignment.

This module provides functions to score resume/profile matches against
job requirements using keyword and qualification matching.
"""

import re
from typing import Tuple

from resume_tailorer.analyzers.term_match import mentions

# JD filler that must not count as evidence a candidate already has a qualification.
_QUALIFICATION_STOPWORDS = frozenset({
    "with", "from", "this", "that", "have", "must", "including", "related",
    "experience", "years", "year", "strong", "ability", "knowledge", "skills",
    "required", "using", "working", "building", "proven", "excellent",
    "plus", "such", "into", "over", "than", "both", "able", "well",
    "good", "high", "role", "position", "field", "work", "team",
    "your", "their", "them", "will", "would", "could", "should",
    "need", "needs", "needed", "across", "within", "about", "other",
    "more", "most", "some", "also", "preferred", "minimum", "highly",
    "demonstrated", "responsible", "responsibilities",
})


def calculate_keyword_alignment(
    resume_text: str, required_keywords: list[str]
) -> Tuple[float, list[str], list[str]]:
    """
    Calculate keyword alignment score between resume and required keywords.

    Args:
        resume_text: The resume/profile text to search in
        required_keywords: List of keywords to match

    Returns:
        Tuple of (score: float 0-1.0, matched: list[str], missing: list[str])
        - score: Ratio of matched keywords to total required keywords
        - matched: List of keywords found in resume
        - missing: List of keywords not found in resume
    """
    matched = []
    missing = []

    # Convert resume text to lowercase for case-insensitive matching
    resume_text_lower = resume_text.lower()

    for keyword in required_keywords:
        if mentions(keyword, resume_text):
            matched.append(keyword)
        else:
            missing.append(keyword)

    # Calculate score: matched / total
    total = len(required_keywords)
    score = len(matched) / total if total > 0 else 0.0

    return score, matched, missing


def _semantic_match_qualification(
    profile_text: str, qualification: str, threshold: float = 0.7
) -> bool:
    """
    Check if a qualification is semantically matched in profile text.

    A qualification is considered matched if at least 'threshold' (default 70%)
    of its key words (words longer than 3 characters) are found in the profile.

    Args:
        profile_text: The profile/resume text to search in
        qualification: The qualification string to match
        threshold: Minimum ratio of key words to match (default 0.7 = 70%)

    Returns:
        True if the qualification is semantically matched, False otherwise
    """
    return qualification_match_ratio(profile_text, qualification) >= threshold


# Common tech acronyms that are the ONLY substantive word in a qualification
# phrase (e.g. "Experience with AWS") but are 3 characters or shorter, so the
# general 4+-character filter below drops them -- leaving zero distinctive
# words and forcing a false ratio of 0.0 (observed live, 2026-09-21: "AWS"
# was clearly present in the profile but "Experience with AWS" still scored
# 0.0 and got classified Category E, "truly missing"). Checked in addition
# to, not instead of, the 4+-character words.
_SHORT_TECH_ACRONYMS = frozenset({
    "aws", "sql", "api", "css", "gcp", "ai", "ml", "ux", "ui", "qa", "pm", "hr", "js", "ci", "cd",
})


def qualification_match_ratio(profile_text: str, qualification: str) -> float:
    """Return the fraction of distinctive qualification words found in profile text."""
    profile_text_lower = profile_text.lower()
    qual_lower = qualification.lower()
    long_words = [
        word
        for word in re.findall(r"\b\w{4,}\b", qual_lower)
        if word not in _QUALIFICATION_STOPWORDS
    ]
    short_acronyms = [
        word
        for word in re.findall(r"\b\w{2,3}\b", qual_lower)
        if word in _SHORT_TECH_ACRONYMS
    ]
    words = long_words + short_acronyms
    if not words:
        return 0.0
    matched_count = 0
    for word in words:
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, profile_text_lower):
            matched_count += 1
    return matched_count / len(words)


def calculate_qualification_alignment(
    profile_text: str,
    required_qualifications: list[str],
    preferred_qualifications: list[str] = None,
) -> Tuple[float, list[str], list[str]]:
    """
    Calculate qualification alignment score between profile and job requirements.

    Args:
        profile_text: The profile/resume text to search in
        required_qualifications: List of required qualifications
        preferred_qualifications: List of preferred qualifications (optional)

    Returns:
        Tuple of (score: float 0-1.0, covered: list[str], missing: list[str])
        - score: Ratio of covered required qualifications to total required
        - covered: List of qualifications found in profile
        - missing: List of qualifications not found in profile
    """
    if preferred_qualifications is None:
        preferred_qualifications = []

    covered = []
    missing = []

    # Check all required qualifications
    for qual in required_qualifications:
        if _semantic_match_qualification(profile_text, qual):
            covered.append(qual)
        else:
            missing.append(qual)

    # Calculate score based on required qualifications only
    total = len(required_qualifications)
    score = len(covered) / total if total > 0 else 0.0

    return score, covered, missing
