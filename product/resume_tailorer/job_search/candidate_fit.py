"""
Candidate Fit Scorer: Compare candidate's actual qualifications against job requirements.

This is DIFFERENT from Resume Match Score:
- Candidate Fit: Based on actual qualifications in CareerTruthProfile
- Resume Match: Based on how well resume communicates those qualifications

Scoring: Weighted average of skills (40%), experience (30%), education (20%), sponsorship (10%)
"""

import re
from datetime import datetime
from typing import List, Optional
from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.job_search.models import JobPosting


class CandidateFitScorer:
    """Scores how well a candidate's qualifications match a job's requirements (0-100)."""

    # Common technical skills to extract from job descriptions
    TECHNICAL_SKILLS = {
        "python", "java", "javascript", "c++", "c#", "go", "rust", "ruby",
        "react", "vue", "angular", "nodejs", "node.js", "express",
        "aws", "azure", "gcp", "google cloud",
        "docker", "kubernetes", "k8s",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "sql", "nosql",
        "rest", "graphql", "grpc",
        "git", "github", "gitlab", "bitbucket",
        "linux", "unix", "windows",
        "ci/cd", "jenkins", "gitlab ci", "github actions", "circleci",
        "html", "css", "scss",
        "typescript", "kotlin", "scala", "php",
        "apache", "nginx", "apache kafka",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
        "django", "flask", "fastapi", "spring", "spring boot",
        "microservices", "kubernetes", "docker",
        "agile", "scrum", "kanban",
        "testing", "jest", "pytest", "junit", "unittest",
        "rds", "s3", "ec2", "lambda", "dynamodb",
        "tableau", "looker", "power bi",
        "scala", "hive", "spark", "hadoop",
        "api", "rest api", "web services",
        "database", "sql", "nosql",
        "system design", "architecture",
        "leadership", "mentoring", "management",
        "communication", "collaboration",
    }

    def score_fit(self, profile: CareerTruthProfile, job: JobPosting) -> float:
        """
        Score how well candidate's qualifications match job requirements (0-100).

        Components:
        - Skills Match (40%): intersection of candidate skills vs required skills
        - Experience Level (30%): years of experience vs requirement (entry/mid/senior)
        - Education (20%): degree type match
        - Sponsorship (10%): whether job offers sponsorship if needed

        Args:
            profile: Candidate's CareerTruthProfile with actual qualifications
            job: JobPosting with requirements

        Returns:
            Float score 0-100
        """
        # Score each component
        skills_score = self._score_skills(profile, job)
        experience_score = self._score_experience(profile, job)
        education_score = self._score_education(profile, job)
        sponsorship_score = self._score_sponsorship(profile, job)

        # Weighted average
        final_score = (
            skills_score * 0.40 +
            experience_score * 0.30 +
            education_score * 0.20 +
            sponsorship_score * 0.10
        )

        return round(float(final_score), 1)

    def _score_skills(self, profile: CareerTruthProfile, job: JobPosting) -> float:
        """
        Score skills match: intersection of candidate skills vs required skills.

        Returns 0-100 based on (matched / required) * 100, capped at 100.
        Defaults to 80 if no required skills found.
        """
        # Extract required skills from job description
        required_skills = self._extract_required_skills(job.description, job.experience_required)

        if not required_skills:
            return 80.0  # Default to neutral if no skills found

        # Get candidate skills (case-insensitive)
        candidate_skills_lower = {s.lower() for s in profile.skills}
        candidate_tools_lower = {t.lower() for t in profile.tools}
        all_candidate_qualifications = candidate_skills_lower | candidate_tools_lower

        # Find matches
        matched_count = 0
        for skill in required_skills:
            if skill.lower() in all_candidate_qualifications:
                matched_count += 1

        # Calculate score
        if required_skills:
            return min((matched_count / len(required_skills)) * 100, 100.0)
        return 80.0

    def _score_experience(self, profile: CareerTruthProfile, job: JobPosting) -> float:
        """
        Score experience level match.

        Levels:
        - Entry: 0-2 years
        - Mid: 3-7 years
        - Senior: 8+ years

        Match scoring:
        - Exact level match: 100
        - One level off: 70
        - Two+ levels off: 40

        Defaults to 80 if no requirement specified.
        """
        if not job.experience_required:
            return 80.0

        # Extract required years (minimum)
        required_years = self._extract_experience_years(job.experience_required)
        if required_years is None:
            return 80.0

        # Calculate candidate's total years of experience
        candidate_years = self._calculate_total_experience_years(profile)

        # Determine levels
        def get_level(years: int) -> str:
            if years <= 2:
                return "entry"
            elif years <= 7:
                return "mid"
            else:
                return "senior"

        required_level = get_level(required_years)
        candidate_level = get_level(candidate_years)

        # Map levels to numeric values for distance calculation
        level_values = {"entry": 0, "mid": 1, "senior": 2}
        required_val = level_values[required_level]
        candidate_val = level_values[candidate_level]

        distance = abs(required_val - candidate_val)

        if distance == 0:
            return 100.0
        elif distance == 1:
            return 70.0
        else:  # distance >= 2
            return 40.0

    def _score_education(self, profile: CareerTruthProfile, job: JobPosting) -> float:
        """
        Score education match.

        Scoring:
        - Exact match or overqualified: 100
        - Related field: 80
        - Has degree (any type): 50
        - No degree: 30

        Defaults to 80 if no requirement specified.
        """
        if not job.education_required:
            return 80.0

        # Parse required education
        required_type = self._parse_education_requirement(job.education_required)

        # Check candidate education
        if not profile.education:
            return 30.0  # No degree

        # Get candidate degree info
        candidate_degree_type = None
        candidate_field = None
        has_any_degree = True

        if profile.education:
            education = profile.education[0]  # Use first/primary education
            candidate_degree_type = self._categorize_degree(education.degree)
            candidate_field = education.field.lower() if education.field else ""

        # Determine match level
        if required_type == "no_requirement":
            return 80.0

        if not has_any_degree:
            return 30.0

        # Check if candidate is overqualified (higher degree than required)
        if candidate_degree_type and required_type:
            candidate_level = self._degree_level(candidate_degree_type)
            required_level = self._degree_level(required_type)

            if candidate_level > required_level:
                return 100.0  # Overqualified is OK

        # Check for exact type match (e.g., Bachelor's for Bachelor's)
        if candidate_degree_type and required_type:
            if candidate_degree_type == required_type:
                # Check if field is related
                if self._is_field_related(candidate_field, required_type):
                    return 100.0
                else:
                    return 80.0  # Right degree, different field

            # Check if related (e.g., Master's for Bachelor's requirement)
            if self._are_degree_types_related(candidate_degree_type, required_type):
                return 80.0

        # Has a degree but different type
        return 50.0

    def _score_sponsorship(self, profile: CareerTruthProfile, job: JobPosting) -> float:
        """
        Score sponsorship availability.

        For now, assume candidate doesn't need sponsorship.
        Score: 100 if sponsorship available or not needed, 0 if needed but not available.

        Returns 100 (assume candidate doesn't need sponsorship unless data shows otherwise).
        """
        # TODO: Once CareerTruthProfile tracks sponsorship needs, implement logic:
        # if profile.needs_sponsorship and not job.sponsorship_available:
        #     return 0.0
        return 100.0

    def _extract_required_skills(self, description: str, experience_text: Optional[str] = None) -> List[str]:
        """
        Extract required skills/keywords from job description.

        Matches against TECHNICAL_SKILLS set using word boundaries.
        Returns list of matched skills.
        """
        combined_text = description.lower()
        if experience_text:
            combined_text += " " + experience_text.lower()

        matched_skills = []
        for skill in self.TECHNICAL_SKILLS:
            # Use word boundary matching to avoid substring matches like "rest" in "interesting"
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, combined_text):
                matched_skills.append(skill)

        return matched_skills

    def _extract_experience_years(self, experience_text: str) -> Optional[int]:
        """
        Extract minimum years from experience requirement text.

        Patterns:
        - "5+ years" -> 5
        - "5-10 years" -> 5
        - "3 years experience" -> 3
        - "0-2 years" -> 0

        Returns minimum year value or None.
        """
        if not experience_text:
            return None

        # Try to find range pattern (e.g., "3-5 years")
        range_match = re.search(r'(\d+)\s*[\-–]\s*(\d+)', experience_text)
        if range_match:
            return int(range_match.group(1))

        # Try to find single number with + or years
        single_match = re.search(r'(\d+)\+?\s*(years|yrs)?', experience_text)
        if single_match:
            return int(single_match.group(1))

        return None

    def _calculate_total_experience_years(self, profile: CareerTruthProfile) -> int:
        """
        Calculate total years of experience from work_experience entries.

        Handles date formats like "2020-2022", "Jan 2020 - Present", etc.
        Uses simple heuristic: count entries as 2 years each if dates unclear.
        """
        if not profile.work_experience:
            return 0

        total_years = 0

        for exp in profile.work_experience:
            years = self._extract_years_from_dates(exp.dates)
            if years:
                total_years += years
            else:
                # Default to 2 years if can't parse dates
                total_years += 2

        return total_years

    def _extract_years_from_dates(self, dates_str: str) -> Optional[int]:
        """
        Extract years worked from date string.

        Patterns:
        - "2020-2022" -> 2 years
        - "Jan 2020 - Present" -> current_year - 2020
        - "2020-Present" -> current_year - 2020
        """
        if not dates_str:
            return None

        # Pattern: "YYYY-YYYY"
        year_match = re.search(r'(\d{4})\s*[\-–]\s*(\d{4})', dates_str)
        if year_match:
            start_year = int(year_match.group(1))
            end_year = int(year_match.group(2))
            return max(1, end_year - start_year)

        # Pattern: "YYYY - Present" or "2020 - Present"
        present_match = re.search(r'(\d{4})\s*[\-–]\s*(present|now|current)', dates_str, re.IGNORECASE)
        if present_match:
            start_year = int(present_match.group(1))
            current_year = datetime.now().year
            return max(1, current_year - start_year)

        return None

    def _parse_education_requirement(self, education_text: str) -> str:
        """
        Parse education requirement and return degree type category.

        Returns:
        - "bachelor" for Bachelor's/BS/BA
        - "master" for Master's/MS/MA
        - "phd" for PhD/Doctorate
        - "associate" for Associate's
        - "high_school" for High School
        - "no_requirement" if none found
        """
        if not education_text:
            return "no_requirement"

        text_lower = education_text.lower()

        if any(x in text_lower for x in ["phd", "doctorate", "doctoral"]):
            return "phd"

        if any(x in text_lower for x in ["master's", "master", "ms ", "m.s.", "ma ", "m.a."]):
            return "master"

        if any(x in text_lower for x in ["bachelor's", "bachelor", "bs ", "b.s.", "ba ", "b.a."]):
            return "bachelor"

        if any(x in text_lower for x in ["associate's", "associate", "aa ", "a.a.", "as ", "a.s."]):
            return "associate"

        if any(x in text_lower for x in ["high school", "hs ", "secondary"]):
            return "high_school"

        return "no_requirement"

    def _categorize_degree(self, degree: str) -> str:
        """
        Categorize a degree into type.

        Returns one of: "bachelor", "master", "phd", "associate", "high_school", "other"
        """
        if not degree:
            return "other"

        degree_lower = degree.lower()

        if any(x in degree_lower for x in ["phd", "doctorate", "dr.", "d."]):
            return "phd"

        if any(x in degree_lower for x in ["master", "ms", "m.s.", "ma", "m.a."]):
            return "master"

        if any(x in degree_lower for x in ["bachelor", "bs", "b.s.", "ba", "b.a."]):
            return "bachelor"

        if any(x in degree_lower for x in ["associate", "aa", "a.a.", "as", "a.s."]):
            return "associate"

        if any(x in degree_lower for x in ["high school", "hs"]):
            return "high_school"

        return "other"

    def _is_field_related(self, field: str, degree_type: str) -> bool:
        """
        Check if a field is related to the required degree type.

        For now, check if field contains common keywords for technical fields
        when required_type is "bachelor" or "master".
        """
        if not field:
            return False

        field_lower = field.lower()

        technical_keywords = {
            "computer science", "software", "engineering", "computer engineering",
            "information technology", "it ", "data science", "mathematics",
            "physics", "electrical", "mechanical", "civil", "chemical",
            "systems engineering", "database", "networking", "security"
        }

        for keyword in technical_keywords:
            if keyword in field_lower:
                return True

        return False

    def _are_degree_types_related(self, candidate_type: str, required_type: str) -> bool:
        """
        Check if candidate's degree type can satisfy required degree type.

        E.g., Master's satisfies Bachelor's requirement.
        """
        # Master's or PhD satisfies Bachelor's
        if required_type == "bachelor" and candidate_type in ["master", "phd"]:
            return True

        # PhD satisfies Master's requirement
        if required_type == "master" and candidate_type == "phd":
            return True

        # Associate's partially satisfies Bachelor's (return False, let caller decide)
        # (Handled separately in _score_education)

        return False

    def _degree_level(self, degree_type: str) -> int:
        """
        Return numeric level for degree type for comparison.

        Higher number = higher degree.
        """
        levels = {
            "high_school": 0,
            "associate": 1,
            "bachelor": 2,
            "master": 3,
            "phd": 4,
            "other": 1,  # Treat unknown as associate level
        }
        return levels.get(degree_type, 1)
