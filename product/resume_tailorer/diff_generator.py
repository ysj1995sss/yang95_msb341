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
            # Match lines starting with -, * or • (the same bullet markers the
            # PDF generator and resume parser accept).
            if re.match(r"^[-*•]\s+", line):
                bullet = re.sub(r"^[-*•]\s+", "", line)
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
                # Pair bullets by SIMILARITY, not by index position. Index-based
                # pairing scrambles a reorder with an unrelated reword, and hides
                # genuinely new bullets behind whatever original shares their index.
                orig_slice = list(original[i1:i2])
                tail_slice = list(tailored[j1:j2])

                # Score every (orig, tail) pair in this replace block.
                pairs = []
                for oi, orig_bullet in enumerate(orig_slice):
                    for ti, tail_bullet in enumerate(tail_slice):
                        ratio = difflib.SequenceMatcher(
                            None, orig_bullet, tail_bullet
                        ).ratio()
                        pairs.append((ratio, oi, ti))

                # Greedily match highest-similarity pairs first; each used once.
                pairs.sort(key=lambda p: p[0], reverse=True)
                matched_orig = set()
                matched_tail = set()
                matches = []  # (oi, ti)
                for ratio, oi, ti in pairs:
                    if oi in matched_orig or ti in matched_tail:
                        continue
                    matched_orig.add(oi)
                    matched_tail.add(ti)
                    matches.append((oi, ti))

                for oi, ti in matches:
                    orig_bullet = orig_slice[oi]
                    tail_bullet = tail_slice[ti]
                    if self._is_rephrased(orig_bullet, tail_bullet):
                        change_type = "rephrased"
                        reasoning = "Same fact, different wording to match job keywords"
                    else:
                        change_type = "modified"
                        reasoning = "Content changed"

                    changes.append(
                        BulletChange(
                            original=orig_bullet,
                            tailored=tail_bullet,
                            change_type=change_type,
                            reasoning=reasoning,
                        )
                    )

                # Unmatched originals were dropped, not rephrased into anything.
                for oi, orig_bullet in enumerate(orig_slice):
                    if oi not in matched_orig:
                        changes.append(
                            BulletChange(
                                original=orig_bullet,
                                tailored="",
                                change_type="removed",
                                reasoning="Deprioritized for space; not directly relevant to this job",
                            )
                        )

                # Unmatched tailored bullets are genuinely new content.
                for ti, tail_bullet in enumerate(tail_slice):
                    if ti not in matched_tail:
                        changes.append(
                            BulletChange(
                                original="",
                                tailored=tail_bullet,
                                change_type="added",
                                reasoning="NEW BULLET - should not occur if tailoring is truthful",
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

    _METRIC_PATTERN = re.compile(r"\d+(?:\.\d+)?%")
    _TECH_KEYWORDS = [
        "python", "java", "javascript", "c++", "rust", "go",
        "aws", "azure", "gcp", "kubernetes", "docker", "terraform",
        "react", "vue", "angular", "node", "flask", "django",
    ]
    # Deliberately small and generic (articles/prepositions/conjunctions),
    # not domain-specific -- this check needs to work for a marketing
    # resume exactly as well as a tech one, unlike _TECH_KEYWORDS above.
    _STOPWORDS = {
        "a", "an", "the", "and", "or", "of", "to", "for", "with", "in", "on",
        "at", "by", "from", "into", "across", "through", "as", "that", "this",
        "these", "those", "is", "was", "were", "are", "be", "been", "being",
        "it", "its", "their", "them", "they", "which", "who", "will", "not",
        "such", "than", "then", "over", "under", "up", "down", "out", "per",
    }
    # A synonym swap among common resume action verbs/connectors is always
    # safe rephrasing -- it changes HOW an accomplishment is described, not
    # WHAT it claims -- so these are exempt from the "genuinely new word"
    # check below. Only a new NOUN/ADJECTIVE characterizing the
    # accomplishment itself (e.g. "loyalty", found live 2026-09-23) should
    # trip that check; a new verb like "developed" or a connector like
    # "using" should not. Not exhaustive by design -- broad enough to cover
    # common resume verbs without trying to enumerate every synonym.
    _SAFE_REPHRASE_WORDS = {
        "led", "built", "developed", "managed", "drove", "increased", "achieved",
        "created", "delivered", "executed", "launched", "spearheaded", "directed",
        "coordinated", "established", "implemented", "generated", "optimized",
        "negotiated", "secured", "using", "utilizing", "leveraging", "supported",
        "enabled", "facilitated", "designed", "improved", "boosted", "grew",
        "expanded", "streamlined", "enhanced", "conducted", "analyzed",
        "presented", "collaborated", "partnered", "translated", "aligned",
        "distilled", "adopted", "targeting", "targeted", "identifying",
        "identified", "synthesizing", "synthesized", "crafting", "crafted",
        "refined", "diagnosed", "resulting", "leading", "driving", "recognized",
    }

    # Common suffixes stripped before comparing words, so a plain verb-tense
    # or plural change ("identifying" vs "identify", "strategies" vs
    # "strategy") isn't mistaken for dropping the word entirely -- only
    # applied to words long enough that stripping still leaves a real stem
    # (avoids "was"->"w" nonsense).
    _SUFFIXES = ("ing", "edly", "ed", "ies", "es", "s")

    @classmethod
    def _stem(cls, word: str) -> str:
        for suffix in cls._SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                stem = word[: -len(suffix)]
                return stem + "y" if suffix == "ies" else stem
        return word

    @classmethod
    def _content_words(cls, text: str) -> set:
        return {
            w for w in re.findall(r"[a-zA-Z']+", text.lower())
            if len(w) > 3 and w not in cls._STOPWORDS
        }

    @classmethod
    def _content_stems(cls, text: str) -> set:
        return {cls._stem(w) for w in cls._content_words(text)}

    def check_semantic_drift(self, original: str, new: str) -> List[str]:
        """
        Hard, code-level guard against narrowing or changing an existing
        bullet's claim -- found live (2026-09-23): "front-store growth
        strategy" was rewritten to "front-store acquisition strategy",
        silently narrowing a broad growth claim to a specific acquisition
        claim even though "acquisition" was itself a legitimate word used
        elsewhere in the resume. That's a DIFFERENT failure mode from
        fabrication (the word wasn't invented) -- it's substituting one of
        the original bullet's own content words for a different one,
        changing what the bullet actually claims. A rephrase may ADD words
        freely; it must never DROP a substantive word the original bullet
        used to say what was accomplished. Compares STEMS (not exact
        words) so a plain tense/plural change doesn't false-positive.

        _SAFE_REPHRASE_WORDS (common resume action verbs/connectors) are
        exempt from "must not drop" -- found live (2026-09-23), a SECOND
        real bug from the same check: rewriting "Developed a front-store
        growth strategy" to start with a different verb (e.g. "Led")
        wrongly counted as dropping "developed" and blocked an otherwise
        legitimate rephrase. Swapping one action verb for another changes
        HOW the accomplishment is described, not WHAT was accomplished --
        exactly the same distinction the fabrication check already makes.
        """
        original_words = self._content_words(original)
        new_stems = self._content_stems(new)
        safe_stems = {self._stem(w) for w in self._SAFE_REPHRASE_WORDS}
        dropped = {
            w for w in original_words
            if self._stem(w) not in new_stems and self._stem(w) not in safe_stems
        }
        if dropped:
            return [
                f"SEMANTIC DRIFT: dropped word(s) {sorted(dropped)} from the original bullet "
                f"'{original}' -- rewrite changes what was claimed, not just how it's phrased"
            ]
        return []

    @staticmethod
    def _profile_blob(profile: CareerTruthProfile) -> str:
        """
        Every piece of profile text a "fabrication" check should treat as
        already-true, lowercased. Previously missing `education[*].notes`
        and `profile.summary` -- found live (2026-09-22): a verbatim
        "Top 1% of Class" line (stored as an EducationEntry note, not a
        work-experience bullet) was flagged as a fabricated "1%" metric
        purely because this blob never included education notes at all.
        """
        parts = list(profile.skills) + list(profile.tools) + list(profile.certifications)
        for job in profile.work_experience:
            parts.extend(job.accomplishments)
            parts.extend(job.responsibilities)
        for edu in profile.education:
            parts.extend(edu.notes)
        if profile.summary:
            parts.append(profile.summary)
        return " ".join(parts).lower()

    def check_bullet_pair_fabrication_risk(
        self, original: str, new: str, profile: CareerTruthProfile
    ) -> List[str]:
        """
        Per-pair fabrication check for the DOCX splice pipeline, where the
        old-bullet-to-new-bullet mapping is already known by paragraph
        index -- unlike `_check_fabrication_risks`, which has to pair
        tailored bullets to profile evidence with no known correspondence
        to a specific original bullet. A metric/keyword already present in
        THIS bullet's own original text is never flagged, on top of the
        profile-wide blob -- carrying over an existing fact isn't a risk.
        """
        issues = []
        trusted_blob = self._profile_blob(profile) + " " + original.lower()
        new_lower = new.lower()

        for metric in self._METRIC_PATTERN.findall(new):
            if metric.lower() not in trusted_blob and metric not in trusted_blob:
                issues.append(
                    f"⚠️ FABRICATION RISK: metric '{metric}' mentioned in '{new}' "
                    "but not in the original bullet or profile"
                )

        for tech in self._TECH_KEYWORDS:
            pattern = self._tech_pattern(tech)
            if re.search(pattern, new_lower) and not re.search(pattern, trusted_blob):
                issues.append(
                    f"⚠️ FABRICATION RISK: '{tech}' mentioned in '{new}' but not in the original bullet or profile"
                )

        # Generalizes the tech-keyword check above to any domain -- found
        # live, 2026-09-23, TWICE: "loyalty" was added to describe a
        # program on a marketing resume, a term _TECH_KEYWORDS could never
        # catch since it only knows tech stack names. A first version of
        # this check only flagged 2+ new words at once (reasoning: a single
        # new word is often just normal stylistic rephrasing -- a different
        # verb, a connector), but a live re-test showed that threshold
        # missing the exact "loyalty" case again, since it was the only new
        # word in that edit. Callers (DocxBulletTailorer) now treat any hit
        # here as a HARD REJECT, not just a warning, so a _SAFE_REPHRASE_WORDS
        # exemption for common resume action verbs/connectors is essential --
        # without it, nearly every legitimate rephrase (which almost always
        # introduces at least one new verb) would get rejected too. Only a
        # new NOUN/ADJECTIVE characterizing the accomplishment itself still
        # trips this.
        trusted_stems = self._content_stems(trusted_blob)
        original_stems = self._content_stems(original)
        safe_stems = {self._stem(w) for w in self._SAFE_REPHRASE_WORDS}
        genuinely_new = {
            w for w in self._content_words(new)
            if self._stem(w) not in trusted_stems
            and self._stem(w) not in original_stems
            and self._stem(w) not in safe_stems
        }
        if genuinely_new:
            issues.append(
                f"⚠️ POSSIBLY UNVERIFIED: new term(s) {sorted(genuinely_new)} in '{new}' "
                "not grounded in the original bullet or profile -- review before using"
            )

        return issues

    def _check_fabrication_risks(
        self, tailored_bullets: List[str], profile: CareerTruthProfile
    ) -> List[str]:
        """Check tailored resume for skills/tools not present anywhere in the profile."""
        issues = []

        profile_blob = self._profile_blob(profile)

        profile_metrics = set(self._METRIC_PATTERN.findall(profile_blob))
        reported_metrics = set()
        for bullet in tailored_bullets:
            for metric in self._METRIC_PATTERN.findall(bullet):
                if metric in reported_metrics:
                    continue
                if metric.lower() not in profile_metrics and metric not in profile_metrics:
                    issues.append(
                        f"⚠️ FABRICATION RISK: metric '{metric}' mentioned in '{bullet}' "
                        "but not in original resume"
                    )
                    reported_metrics.add(metric)

        # Dedup: don't repeat the same tech keyword across multiple bullets.
        reported = set()
        for bullet in tailored_bullets:
            bullet_lower = bullet.lower()
            for tech in self._TECH_KEYWORDS:
                if tech in reported:
                    continue
                pattern = self._tech_pattern(tech)
                if re.search(pattern, bullet_lower) and not re.search(
                    pattern, profile_blob
                ):
                    issues.append(
                        f"⚠️ FABRICATION RISK: '{tech}' mentioned in '{bullet}' but not in original resume"
                    )
                    reported.add(tech)

        return issues

    @staticmethod
    def _tech_pattern(tech: str) -> str:
        """Word-boundary regex for a tech keyword, safe for tokens like 'c++'.

        A plain ``\\b`` after '+' would require a following word character and
        never match "c++", so boundaries are only asserted on alphanumeric edges.
        Prevents false hits such as "go" inside "algorithm".
        """
        left = r"(?<!\w)" if tech[:1].isalnum() else ""
        right = r"(?!\w)" if tech[-1:].isalnum() else ""
        return left + re.escape(tech) + right
