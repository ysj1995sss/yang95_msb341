"""Resume diff generator: compare original vs. tailored resumes with reasoning."""

from dataclasses import dataclass, field
from typing import List
import difflib
import re

from .models import CareerTruthProfile


@dataclass
class BulletChange:
    """A single change from original to tailored bullet."""
    original: str
    tailored: str
    change_type: str  # "rephrased", "reordered", "highlighted", "removed", "fabrication_risk"
    reasoning: str


@dataclass
class ResumeDiffReport:
    """Complete diff report between original and tailored resume."""
    original_bullets: List[str]
    tailored_bullets: List[str]
    changes: List[BulletChange] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)  # Fabrication risks, warnings


class DiffGenerator:
    """Generate a detailed diff report comparing original vs. tailored resumes."""

    def __init__(self):
        pass

    def generate_diff(
        self, career_profile: CareerTruthProfile, tailored_text: str
    ) -> ResumeDiffReport:
        """
        Compare original resume (from Career Truth Profile) to tailored text.

        Returns a ResumeDiffReport with identified changes and reasoning.

        Args:
            career_profile: Structured career data from the original resume
            tailored_text: Tailored resume as plain text

        Returns:
            ResumeDiffReport with original_bullets, tailored_bullets, changes, issues
        """
        # Extract original bullets from profile
        original_bullets = self._extract_bullets_from_profile(career_profile)

        # Extract tailored bullets from text
        tailored_bullets = self._extract_bullets_from_text(tailored_text)

        # Compare and generate changes
        changes = self._compute_changes(original_bullets, tailored_bullets, career_profile)

        # Check for fabrication risks
        issues = self._check_fabrication_risks(
            tailored_bullets, career_profile
        )

        return ResumeDiffReport(
            original_bullets=original_bullets,
            tailored_bullets=tailored_bullets,
            changes=changes,
            issues=issues,
        )

    def _extract_bullets_from_profile(self, profile: CareerTruthProfile) -> List[str]:
        """Extract all accomplishment bullets from Career Truth Profile."""
        bullets = []

        for job in profile.work_experience:
            for accomplishment in job.accomplishments:
                bullets.append(accomplishment)

        return bullets

    def _extract_bullets_from_text(self, text: str) -> List[str]:
        """Extract bullet points from plain-text resume."""
        lines = text.split("\n")
        bullets = []

        for line in lines:
            line = line.strip()
            # Match lines starting with - or •
            if re.match(r"^[-•]\s+", line):
                bullet = re.sub(r"^[-•]\s+", "", line)
                if bullet:
                    bullets.append(bullet)

        return bullets

    def _compute_changes(
        self, original: List[str], tailored: List[str], profile: CareerTruthProfile
    ) -> List[BulletChange]:
        """Compute which bullets changed and how."""
        changes = []

        # Use SequenceMatcher to find best matches
        matcher = difflib.SequenceMatcher(None, original, tailored)

        # Detect reordering: same set of bullets, different order
        if (
            len(original) == len(tailored)
            and sorted(original) == sorted(tailored)
            and original != tailored
        ):
            for orig_idx, orig in enumerate(original):
                tail_idx = tailored.index(orig)
                if tail_idx != orig_idx:
                    changes.append(
                        BulletChange(
                            original=orig,
                            tailored=orig,
                            change_type="reordered",
                            reasoning="Bullet order changed to prioritize relevance to this job",
                        )
                    )
            return changes

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                # One or more bullets were changed
                for orig_idx in range(i1, i2):
                    tail_idx = j1 + (orig_idx - i1)
                    if tail_idx < j2:
                        orig = original[orig_idx]
                        tail = tailored[tail_idx]

                        # Determine change type
                        if self._is_rephrased(orig, tail):
                            change_type = "rephrased"
                            reasoning = "Same fact, different wording to match job keywords"
                        else:
                            change_type = "modified"
                            reasoning = "Content changed"

                        changes.append(
                            BulletChange(
                                original=orig,
                                tailored=tail,
                                change_type=change_type,
                                reasoning=reasoning,
                            )
                        )

            elif tag == "delete":
                # Bullets removed (only if not reordered)
                for idx in range(i1, i2):
                    changes.append(
                        BulletChange(
                            original=original[idx],
                            tailored="",
                            change_type="removed",
                            reasoning="Deprioritized for space; not directly relevant to this job",
                        )
                    )

            elif tag == "insert":
                # New bullets added (should never happen from Career Truth Profile)
                for idx in range(j1, j2):
                    changes.append(
                        BulletChange(
                            original="",
                            tailored=tailored[idx],
                            change_type="added",
                            reasoning="NEW BULLET - should not occur if tailoring is truthful",
                        )
                    )

        return changes

    def _is_rephrased(self, original: str, tailored: str) -> bool:
        """Check if tailored is a rephrase of original (same facts, different wording)."""
        # Simple heuristic: if they share key words and are similar length, likely a rephrase
        orig_words = set(original.lower().split())
        tail_words = set(tailored.lower().split())

        # Remove common stop words
        stop_words = {"a", "an", "the", "and", "or", "to", "in", "of", "for", "with"}
        orig_words -= stop_words
        tail_words -= stop_words

        # If at least half of the smaller bullet's distinctive words reappear
        # in the other, treat it as a rephrase of the same underlying fact
        # rather than a wholesale content change.
        if orig_words and tail_words:
            overlap = len(orig_words & tail_words) / min(len(orig_words), len(tail_words))
            return overlap >= 0.5

        return False

    def _check_fabrication_risks(
        self, tailored_bullets: List[str], profile: CareerTruthProfile
    ) -> List[str]:
        """Check tailored resume for skills/tools/companies not in profile."""
        issues = []

        # Collect all known skills, tools, companies from profile
        known_skills = set(s.lower() for s in profile.skills)
        known_tools = set(t.lower() for t in profile.tools)
        known_companies = set(
            job.employer.lower() for job in profile.work_experience if job.employer
        )

        for bullet in tailored_bullets:
            bullet_lower = bullet.lower()

            # Look for programming languages or tools that weren't in profile
            tech_keywords = [
                "python", "java", "javascript", "c++", "rust", "go",
                "aws", "azure", "gcp", "kubernetes", "docker", "terraform",
                "react", "vue", "angular", "node", "flask", "django",
            ]

            for tech in tech_keywords:
                if tech in bullet_lower and tech not in known_skills and tech not in known_tools:
                    issues.append(
                        f"⚠️ FABRICATION RISK: '{tech}' mentioned in '{bullet}' but not in original resume"
                    )

        return issues
