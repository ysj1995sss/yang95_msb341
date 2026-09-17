"""
Scoring utilities for calculating keyword and qualification alignment.

This module provides functions to score resume/profile matches against
job requirements using keyword and qualification matching.
"""

import re
from typing import Tuple


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
        # Use word boundary regex for exact word matching (case-insensitive)
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        if re.search(pattern, resume_text_lower):
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
    profile_text_lower = profile_text.lower()
    qual_lower = qualification.lower()

    # Extract key words (words longer than 3 characters) from qualification
    words = re.findall(r"\b\w{4,}\b", qual_lower)

    if not words:
        # If no key words, do simple substring match
        return qual_lower in profile_text_lower

    # Count how many key words are found in profile
    matched_count = 0
    for word in words:
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, profile_text_lower):
            matched_count += 1

    # Check if matched count meets threshold
    match_ratio = matched_count / len(words)
    return match_ratio >= threshold


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
