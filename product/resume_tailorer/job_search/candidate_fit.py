"""
Candidate Fit Scorer: Compare candidate's actual qualifications against job requirements.

This is DIFFERENT from Resume Match Score:
- Candidate Fit: Based on actual qualifications in CareerTruthProfile
- Resume Match: Based on how well resume communicates those qualifications

cf-v2: Eligibility / Core / Preferred / Evidence Confidence + overall,
with competency-map transferable evidence.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from resume_tailorer.analyzers.competency_map import (
    COMPETENCY_EVIDENCE_PATTERNS,
    extract_profile_sentences,
    find_education_status_evidence,
    find_transferable_evidence,
)
from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.job_search.models import (
    DIRECT_VERIFIED,
    FitEvidence,
    FitResult,
    JobPosting,
    STRONGLY_SUPPORTED,
    TRANSFERABLE_PARTIAL,
    UNSUPPORTED,
)


class CandidateFitScorer:
    """Scores how well a candidate's qualifications match a job's requirements (0-100)."""

    SCORING_VERSION = "cf-v2"

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
        "project management", "business analysis", "data analytics",
    }

    def score_fit(self, profile: CareerTruthProfile, job: JobPosting) -> Optional[float]:
        """Overall fit 0-100, or None when the posting states nothing that can be scored."""
        detailed = self.score_fit_detailed(profile, job)
        return None if detailed.overall_fit is None else float(detailed.overall_fit)

    def score_fit_detailed(self, profile: CareerTruthProfile, job: JobPosting) -> FitResult:
        """Explainable Candidate Fit with component scores and evidence."""
        sentences = extract_profile_sentences(profile)
        evidence: List[FitEvidence] = []
        strong_matches: List[str] = []
        partial_matches: List[str] = []
        true_gaps: List[str] = []
        unknown: List[str] = []

        required_skills = self._extract_required_skills(
            job.description, job.experience_required
        )
        preferred_skills = self._extract_preferred_skills(job.description)
        preferred_set = {s.lower() for s in preferred_skills}
        required_skills = [s for s in required_skills if s.lower() not in preferred_set]

        core_hits = 0.0
        core_total = 0
        evidenced = 0
        considered = 0

        for skill in required_skills:
            core_total += 1
            considered += 1
            level, quote = self._match_requirement(skill, profile, sentences)
            if level in (DIRECT_VERIFIED, STRONGLY_SUPPORTED):
                core_hits += 1
                evidenced += 1
                strong_matches.append(skill)
                evidence.append(FitEvidence(skill, level, quote))
            elif level == TRANSFERABLE_PARTIAL:
                core_hits += 0.6
                evidenced += 1
                partial_matches.append(skill)
                evidence.append(FitEvidence(skill, level, quote))
            else:
                true_gaps.append(skill)
                evidence.append(FitEvidence(skill, UNSUPPORTED, ""))

        req_text = self._section_after(
            (job.description or "").lower(),
            ("requirements:", "required:", "you must", "minimum qualifications"),
        ) or (job.description or "").lower()[:900]
        for competency in COMPETENCY_EVIDENCE_PATTERNS:
            if competency.lower() not in req_text:
                continue
            if any(competency.lower() == s.lower() for s in required_skills):
                continue
            core_total += 1
            considered += 1
            te = find_transferable_evidence(competency, sentences)
            if te and te.level == "strong":
                core_hits += 1
                evidenced += 1
                strong_matches.append(competency)
                evidence.append(
                    FitEvidence(competency, STRONGLY_SUPPORTED, te.evidence_text)
                )
            elif te and te.level == "partial":
                core_hits += 0.6
                evidenced += 1
                partial_matches.append(competency)
                evidence.append(
                    FitEvidence(competency, TRANSFERABLE_PARTIAL, te.evidence_text)
                )
            else:
                true_gaps.append(competency)
                evidence.append(FitEvidence(competency, UNSUPPORTED, ""))

        core_capabilities: Optional[float]
        if core_total == 0:
            core_capabilities = None
            unknown.append("required skills not stated")
        else:
            core_capabilities = min(100.0, (core_hits / core_total) * 100.0)

        pref_hits = 0.0
        pref_total = len(preferred_skills)
        preferred_qualifications: Optional[float]
        if pref_total == 0:
            preferred_qualifications = None
        else:
            for skill in preferred_skills:
                considered += 1
                level, quote = self._match_requirement(skill, profile, sentences)
                if level in (DIRECT_VERIFIED, STRONGLY_SUPPORTED):
                    pref_hits += 1
                    evidenced += 1
                    strong_matches.append(f"preferred: {skill}")
                    evidence.append(FitEvidence(f"preferred: {skill}", level, quote))
                elif level == TRANSFERABLE_PARTIAL:
                    pref_hits += 0.6
                    evidenced += 1
                    partial_matches.append(f"preferred: {skill}")
                    evidence.append(FitEvidence(f"preferred: {skill}", level, quote))
                else:
                    unknown.append(f"preferred unmet: {skill}")
                    evidence.append(FitEvidence(f"preferred: {skill}", UNSUPPORTED, ""))
            preferred_qualifications = min(100.0, (pref_hits / pref_total) * 100.0)

        experience_text = job.experience_required
        if not experience_text or str(experience_text).strip().lower() in (
            "unknown",
            "full-time",
            "part-time",
            "contract",
            "internship",
        ):
            if experience_text and str(experience_text).strip().lower() in (
                "full-time",
                "part-time",
                "contract",
                "internship",
            ):
                experience_text = None
            years_from_desc = self._extract_experience_years(job.description or "")
            if years_from_desc is not None:
                experience_text = f"{years_from_desc}+ years"

        education_score = self._score_education(profile, job)
        experience_score = self._score_experience_from_text(profile, experience_text)
        sponsorship_score = self._score_sponsorship(profile, job)

        if job.education_required:
            considered += 1
            edu_ev = find_education_status_evidence(job.education_required, profile)
            if edu_ev:
                evidenced += 1
                strong_matches.append("education requirement")
                evidence.append(
                    FitEvidence(job.education_required, DIRECT_VERIFIED, edu_ev)
                )
            elif education_score is not None and education_score < 50:
                true_gaps.append(job.education_required)

        if experience_text:
            considered += 1
            if experience_score is not None and experience_score >= 70:
                evidenced += 1
            elif experience_score is not None and experience_score < 70:
                true_gaps.append(f"experience: {experience_text}")

        eligibility_parts: List[tuple[float, float]] = []
        if education_score is not None:
            eligibility_parts.append((education_score, 0.4))
        if experience_score is not None:
            eligibility_parts.append((experience_score, 0.5))
        if sponsorship_score is not None:
            eligibility_parts.append((sponsorship_score, 0.1))

        eligibility: Optional[float]
        if not eligibility_parts:
            eligibility = None
            unknown.append("eligibility requirements not stated")
        else:
            tw = sum(w for _, w in eligibility_parts)
            eligibility = sum(s * w for s, w in eligibility_parts) / tw

        evidence_confidence: Optional[float]
        if considered == 0:
            evidence_confidence = None
        else:
            evidence_confidence = min(100.0, (evidenced / considered) * 100.0)

        components: List[tuple[float, float]] = []
        if eligibility is not None:
            components.append((eligibility, 0.25))
        if core_capabilities is not None:
            components.append((core_capabilities, 0.45))
        if preferred_qualifications is not None:
            components.append((preferred_qualifications, 0.15))
        if evidence_confidence is not None:
            components.append((evidence_confidence, 0.15))

        if core_capabilities is None and experience_score is None:
            overall = None
        elif not components:
            overall = None
        else:
            tw = sum(w for _, w in components)
            overall = round(sum(s * w for s, w in components) / tw, 1)

        return FitResult(
            overall_fit=overall,
            eligibility=round(eligibility, 1) if eligibility is not None else None,
            core_capabilities=(
                round(core_capabilities, 1) if core_capabilities is not None else None
            ),
            preferred_qualifications=(
                round(preferred_qualifications, 1)
                if preferred_qualifications is not None
                else None
            ),
            evidence_confidence=(
                round(evidence_confidence, 1) if evidence_confidence is not None else None
            ),
            strong_matches=strong_matches,
            partial_matches=partial_matches,
            true_gaps=true_gaps,
            unknown=unknown,
            evidence=evidence,
            scoring_version=self.SCORING_VERSION,
        )

    def _match_requirement(
        self,
        requirement: str,
        profile: CareerTruthProfile,
        sentences: List[str],
    ) -> tuple[str, str]:
        req_lower = requirement.lower()
        candidate_skills = {s.lower() for s in profile.skills}
        candidate_tools = {t.lower() for t in profile.tools}
        if req_lower in candidate_skills or req_lower in candidate_tools:
            return DIRECT_VERIFIED, requirement

        te = find_transferable_evidence(requirement, sentences)
        if te and te.level == "strong":
            return STRONGLY_SUPPORTED, te.evidence_text
        if te and te.level == "partial":
            return TRANSFERABLE_PARTIAL, te.evidence_text

        for sentence in sentences:
            if req_lower in sentence.lower():
                return STRONGLY_SUPPORTED, sentence

        return UNSUPPORTED, ""

    def _score_experience_from_text(
        self, profile: CareerTruthProfile, experience_text: Optional[str]
    ) -> Optional[float]:
        if not experience_text or str(experience_text).strip().lower() == "unknown":
            return None
        if str(experience_text).strip().lower() in (
            "full-time",
            "part-time",
            "contract",
            "internship",
            "temporary",
        ):
            return None

        required_years = self._extract_experience_years(experience_text)
        if required_years is None:
            return None

        candidate_years = self._calculate_total_experience_years(profile)

        def get_level(years: int) -> str:
            if years <= 2:
                return "entry"
            elif years <= 7:
                return "mid"
            return "senior"

        level_values = {"entry": 0, "mid": 1, "senior": 2}
        distance = abs(
            level_values[get_level(required_years)]
            - level_values[get_level(candidate_years)]
        )
        if distance == 0:
            return 100.0
        if distance == 1:
            return 70.0
        return 40.0

    def _score_education(self, profile: CareerTruthProfile, job: JobPosting) -> Optional[float]:
        if not job.education_required or str(job.education_required).strip().lower() == "unknown":
            return None

        required_type = self._parse_education_requirement(job.education_required)
        if not profile.education:
            return 30.0

        education = profile.education[0]
        candidate_degree_type = self._categorize_degree(education.degree)
        candidate_field = education.field.lower() if education.field else ""

        if required_type == "no_requirement":
            return 80.0

        if candidate_degree_type and required_type:
            if self._degree_level(candidate_degree_type) > self._degree_level(required_type):
                return 100.0
            if candidate_degree_type == required_type:
                if self._is_field_related(candidate_field, required_type):
                    return 100.0
                return 80.0
            if self._are_degree_types_related(candidate_degree_type, required_type):
                return 80.0
        return 50.0

    def _score_sponsorship(self, profile: CareerTruthProfile, job: JobPosting) -> Optional[float]:
        if job.sponsorship_available is None:
            return None
        # Known status is scorable; without candidate need-flag, do not treat
        # "job does not sponsor" as a candidate capability failure.
        return 100.0

    def _extract_required_skills(
        self, description: str, experience_text: Optional[str] = None
    ) -> List[str]:
        combined_text = (description or "").lower()
        required_section = self._section_after(
            combined_text,
            ("requirements:", "required:", "you must", "minimum qualifications"),
        )
        preferred_section = self._section_after(
            combined_text, ("preferred:", "nice to have", "preferred qualifications")
        )
        search_text = required_section if required_section else combined_text
        if preferred_section and not required_section:
            search_text = combined_text.replace(preferred_section, " ")
        if experience_text and str(experience_text).strip().lower() not in (
            "full-time",
            "part-time",
            "contract",
            "internship",
        ):
            search_text += " " + experience_text.lower()

        matched_skills = []
        for skill in self.TECHNICAL_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, search_text):
                matched_skills.append(skill)
        return matched_skills

    def _extract_preferred_skills(self, description: str) -> List[str]:
        text = (description or "").lower()
        preferred_section = self._section_after(
            text, ("preferred:", "nice to have", "preferred qualifications")
        )
        if not preferred_section:
            return []
        matched = []
        for skill in self.TECHNICAL_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, preferred_section):
                matched.append(skill)
        return matched

    def _section_after(self, text: str, markers: tuple[str, ...]) -> str:
        for marker in markers:
            idx = text.find(marker)
            if idx >= 0:
                return text[idx : idx + 800]
        return ""

    def _extract_experience_years(self, experience_text: str) -> Optional[int]:
        if not experience_text:
            return None
        range_match = re.search(r"(\d+)\s*[\-–]\s*(\d+)", experience_text)
        if range_match:
            return int(range_match.group(1))
        single_match = re.search(
            r"(\d+)\+?\s*(years|yrs)", experience_text, re.IGNORECASE
        )
        if single_match:
            return int(single_match.group(1))
        return None

    def _calculate_total_experience_years(self, profile: CareerTruthProfile) -> int:
        if not profile.work_experience:
            return 0
        total_years = 0
        for exp in profile.work_experience:
            years = self._extract_years_from_dates(exp.dates)
            total_years += years if years else 2
        return total_years

    def _extract_years_from_dates(self, dates_str: str) -> Optional[int]:
        if not dates_str:
            return None
        year_match = re.search(r"(\d{4})\s*[\-–]\s*(\d{4})", dates_str)
        if year_match:
            return max(1, int(year_match.group(2)) - int(year_match.group(1)))
        present_match = re.search(
            r"(\d{4})\s*[\-–]\s*(present|now|current)", dates_str, re.IGNORECASE
        )
        if present_match:
            return max(1, datetime.now().year - int(present_match.group(1)))
        return None

    def _parse_education_requirement(self, education_text: str) -> str:
        if not education_text:
            return "no_requirement"
        text_lower = education_text.lower()
        if any(x in text_lower for x in ["phd", "doctorate", "doctoral"]):
            return "phd"
        if any(x in text_lower for x in ["master's", "master", "ms ", "m.s.", "ma ", "m.a.", "mba"]):
            return "master"
        if any(x in text_lower for x in ["bachelor's", "bachelor", "bs ", "b.s.", "ba ", "b.a."]):
            return "bachelor"
        if any(x in text_lower for x in ["associate's", "associate"]):
            return "associate"
        if any(x in text_lower for x in ["high school", "hs ", "secondary"]):
            return "high_school"
        return "no_requirement"

    def _categorize_degree(self, degree: str) -> str:
        if not degree:
            return "other"
        degree_lower = degree.lower()
        if any(x in degree_lower for x in ["phd", "doctorate"]):
            return "phd"
        if any(x in degree_lower for x in ["master", "ms", "m.s.", "ma", "m.a.", "mba"]):
            return "master"
        if any(x in degree_lower for x in ["bachelor", "bs", "b.s.", "ba", "b.a."]):
            return "bachelor"
        if any(x in degree_lower for x in ["associate"]):
            return "associate"
        return "other"

    def _is_field_related(self, field: str, degree_type: str) -> bool:
        if not field:
            return False
        field_lower = field.lower()
        keywords = {
            "computer science", "software", "engineering", "information technology",
            "data science", "mathematics", "physics",
        }
        return any(k in field_lower for k in keywords)

    def _are_degree_types_related(self, candidate_type: str, required_type: str) -> bool:
        if required_type == "bachelor" and candidate_type in ["master", "phd"]:
            return True
        if required_type == "master" and candidate_type == "phd":
            return True
        return False

    def _degree_level(self, degree_type: str) -> int:
        return {
            "high_school": 0,
            "associate": 1,
            "bachelor": 2,
            "master": 3,
            "phd": 4,
            "other": 1,
        }.get(degree_type, 1)
