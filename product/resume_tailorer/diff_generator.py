"""Resume diff generator: compare original vs. tailored resumes with reasoning."""

from dataclasses import dataclass, field
from typing import List, Optional
import difflib
import re

from .models import CareerTruthProfile
from .analyzers.competency_map import COMPETENCY_EVIDENCE_PATTERNS
from .utils.length_check import bullet_length_delta
from .utils.stemming import stem as _stem


@dataclass
class BulletChange:
    """A single change from original to tailored bullet."""
    original: str
    tailored: str
    change_type: str  # "rephrased", "reordered", "highlighted", "removed", "fabrication_risk"
    reasoning: str
    similarity: float | None = None


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

        # Check for fabrication risks and semantic drift.
        #
        # Previously this called a separate, older _check_fabrication_risks
        # method (metric + fixed tech-keyword list only, no semantic-drift
        # check at all) -- the exact pre-decision-008 limitation that let
        # "loyalty" slip through undetected on the DOCX path before it was
        # fixed there. That fix (check_bullet_pair_fabrication_risk,
        # check_semantic_drift: generalized beyond tech keywords, core/
        # elaboration clause split, evidence-backed competency-label
        # exemption) never made it to this freeform/PDF path, since it
        # validates per-bullet with a known original/new pairing that this
        # path didn't have. _compute_changes above already produces that
        # same pairing (via its own similarity-based matching), so this
        # reuses the SAME checks instead of a second, weaker
        # implementation -- one fabrication/drift system, not two.
        #
        # A pure add/remove has no original to pair against;
        # check_bullet_pair_fabrication_risk still runs for pure adds with
        # original="" (everything in the bullet is then checked only
        # against the profile, which is exactly correct for a bullet that
        # has no prior version to compare wording to). check_semantic_drift
        # needs a real original, so it's skipped for pure adds/removes.
        #
        # already_reported is shared across every call in this loop (not
        # the default fresh-set-per-call) so the same fabricated term
        # flagged in two different bullets is reported once, not once per
        # bullet -- the cross-bullet dedup _check_fabrication_risks used to
        # provide.
        # Step 15 (length control): the freeform/PDF path previously had no
        # bullet-level length signal at all -- length was a purely post-hoc
        # rendering concern (PDFGenerator adjusting font/margins to fit).
        # bullet_length_delta already existed for exactly this purpose but
        # had no caller anywhere in the codebase; wired in here using the
        # same per-pair loop as the checks above.
        issues: List[str] = []
        seen_issues: set = set()
        already_reported: set = set()
        for change in changes:
            if not change.tailored:
                continue  # pure removal -- nothing new to check
            if change.original:
                for issue in self.check_semantic_drift(change.original, change.tailored):
                    if issue not in seen_issues:
                        issues.append(issue)
                        seen_issues.add(issue)
                for issue in bullet_length_delta(change.original, change.tailored):
                    if issue not in seen_issues:
                        issues.append(issue)
                        seen_issues.add(issue)
            for issue in self.check_bullet_pair_fabrication_risk(
                change.original, change.tailored, career_profile, already_reported
            ):
                if issue not in seen_issues:
                    issues.append(issue)
                    seen_issues.add(issue)

        return ResumeDiffReport(
            original_bullets=original_bullets,
            tailored_bullets=tailored_bullets,
            changes=changes,
            issues=issues,
        )

    def _extract_bullets_from_profile(self, profile: CareerTruthProfile) -> List[str]:
        """Extract every already-true, bullet-comparable line from the
        Career Truth Profile -- not just work-experience accomplishments.

        Previously only read job.accomplishments. job.responsibilities,
        education notes, skills/tools/certifications, and summary were
        invisible to this pairing step, so ANY tailored bullet built from
        those (100% truthful) categories had no possible match in
        original_bullets and was always misclassified as a fabricated
        "added" bullet by _compute_changes below -- found live (2026-09-28),
        first real end-to-end test with a live LLM: a real resume's
        education honors/scholarships and skills list both got flagged as
        fabricated. This is the exact gap _profile_blob (the
        fabrication-risk check's trusted vocabulary, see its own
        docstring) was already fixed for once before -- just never
        mirrored here, in the step that decides change_type in the first
        place.
        """
        bullets = []

        for job in profile.work_experience:
            bullets.extend(job.accomplishments)
            bullets.extend(job.responsibilities)

        for edu in profile.education:
            bullets.extend(edu.notes)

        bullets.extend(profile.skills)
        bullets.extend(profile.tools)
        bullets.extend(profile.certifications)

        if profile.summary:
            bullets.append(profile.summary)

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
                            similarity=1.0,
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
                matches = []  # (similarity, oi, ti)
                for ratio, oi, ti in pairs:
                    if oi in matched_orig or ti in matched_tail:
                        continue
                    matched_orig.add(oi)
                    matched_tail.add(ti)
                    matches.append((ratio, oi, ti))

                for ratio, oi, ti in matches:
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
                            similarity=ratio,
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
                                similarity=0.0,
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
                                similarity=0.0,
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
                            similarity=0.0,
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
                            similarity=0.0,
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

    @classmethod
    def _stem(cls, word: str) -> str:
        """Strip a plain verb-tense/plural suffix before comparing words, so
        e.g. "identifying" vs "identify" isn't mistaken for dropping the
        word entirely. Shared with competency_map.py's concept
        normalization via utils/stemming.py -- one stemmer, not two."""
        return _stem(word)

    @classmethod
    def _content_words(cls, text: str) -> set:
        return {
            w for w in re.findall(r"[a-zA-Z']+", text.lower())
            if len(w) > 3 and w not in cls._STOPWORDS
        }

    @classmethod
    def _content_stems(cls, text: str) -> set:
        return {cls._stem(w) for w in cls._content_words(text)}

    # Number-bearing tokens (a metric, a scale, a count) -- these anchor
    # the bullet's factual scope/outcome and must never silently
    # disappear in a rewrite, regardless of where in the bullet they sit.
    # The word-based check below (_content_words, `[a-zA-Z']+`) is
    # entirely blind to these -- "15+", "100%", "$120M", "10-person",
    # "60s", "42s", "3x"/"3×" contain no run of 4+ letters -- so this is a
    # real gap it closes, not just a restatement of the word check.
    _METRIC_TOKEN_RE = re.compile(
        r"\$?\d[\d,.]*\s*(?:%|k|m|b|x|×|\+|-person|-year|s\b)?", re.IGNORECASE
    )

    # A bullet's CORE clause (who/what/how-much) is where a word swap
    # changes the underlying claim (the "growth"->"acquisition" bug); the
    # ELABORATION clause after one of these markers is usually purpose/
    # method/outcome framing, where rewording is normal, safe paraphrasing
    # (found live, 2026-09-23: "...to align portfolios and build
    # cross-cultural trust" rephrased to "...coordinating priorities and
    # strengthening cross-cultural collaboration" preserves the real claim
    # despite heavy wording changes, entirely within this clause). Only
    # the FIRST marker split matters -- everything after it is elaboration.
    _ELABORATION_SPLIT_RE = re.compile(r"\bto\b|\bby\b|,|;|\band\b", re.IGNORECASE)

    @classmethod
    def _split_core_and_elaboration(cls, text: str) -> tuple[str, str]:
        match = cls._ELABORATION_SPLIT_RE.search(text)
        if not match or match.start() < 8:  # too early to be a meaningful split
            return text, ""
        return text[: match.start()], text[match.start() :]

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
        changing what the bullet actually claims.

        Two protections, addressing a follow-up fix request that the
        original word-for-word version was "too literal":

        1. METRICS are hard-protected everywhere in the bullet (a check
           the original version didn't actually have -- numbers contain no
           4+ letter run, so the word-based check below never saw them).
        2. Only the bullet's CORE clause (before the first purpose/method/
           list marker -- "to", "by", a comma, a semicolon, "and") requires
           every content word to survive. The ELABORATION clause after that
           marker can be reworded freely (per the fix request's own
           example: "...to align portfolios and build cross-cultural
           trust" -> "...coordinating priorities and strengthening
           cross-cultural collaboration" must PASS, not be rejected merely
           because the wording changed).

        _SAFE_REPHRASE_WORDS (common resume action verbs/connectors) stay
        exempt from "must not drop" in the core clause too -- swapping the
        leading verb (e.g. "Developed" -> "Led") changes HOW something is
        described, not WHAT was accomplished.
        """
        original_metrics = set(m.group().strip() for m in self._METRIC_TOKEN_RE.finditer(original) if m.group().strip())
        new_metrics = set(m.group().strip() for m in self._METRIC_TOKEN_RE.finditer(new) if m.group().strip())
        dropped_metrics = original_metrics - new_metrics
        if dropped_metrics:
            return [
                f"SEMANTIC DRIFT: dropped metric(s) {sorted(dropped_metrics)} from the original bullet "
                f"'{original}' -- a number/scale disappearing changes the claim"
            ]

        core, _elaboration = self._split_core_and_elaboration(original)
        core_words = self._content_words(core)
        new_stems = self._content_stems(new)
        safe_stems = {self._stem(w) for w in self._SAFE_REPHRASE_WORDS}
        dropped = {
            w for w in core_words
            if self._stem(w) not in new_stems and self._stem(w) not in safe_stems
        }
        if dropped:
            return [
                f"SEMANTIC DRIFT: dropped word(s) {sorted(dropped)} from the original bullet's core "
                f"claim '{core.strip()}' -- rewrite changes what was claimed, not just how it's phrased"
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

    @staticmethod
    def _competency_label_words_evidenced_by(original: str) -> set:
        """
        Words from a competency's own name (e.g. "project", "management")
        are exempt from the 'genuinely new word' fabrication check below
        when the ORIGINAL bullet already strongly matches that competency's
        curated evidence patterns -- e.g. a bullet that already says "100%
        on-time delivery" and "risk mitigation" has already earned the
        label "project management" as safe, evidence-backed abstraction
        (fix-request Problem 6). Naming a competency the bullet already
        demonstrates isn't a new unverified claim; it's restating the same
        fact at a higher level. Deliberately requires a STRONG match on the
        bullet's OWN original text (not the whole profile) to stay narrow.
        """
        words = set()
        original_lower = original.lower()
        for competency, patterns in COMPETENCY_EVIDENCE_PATTERNS.items():
            for pattern in patterns["strong"]:
                if re.search(pattern, original_lower, re.IGNORECASE):
                    words.update(re.findall(r"[a-z]{3,}", competency))
                    break
        return words

    def check_bullet_pair_fabrication_risk(
        self, original: str, new: str, profile: CareerTruthProfile,
        already_reported: Optional[set] = None,
    ) -> List[str]:
        """
        Per-pair fabrication check, callable per bullet pair without any
        cross-bullet correspondence tracking (each call is independent by
        default). A metric/keyword already present in THIS bullet's own
        original text is never flagged, on top of the profile-wide blob --
        carrying over an existing fact isn't a risk.

        `already_reported` is an optional MUTABLE set the caller can share
        across multiple calls (e.g. one per bullet in a whole-resume diff)
        so the same fabricated term isn't reported once per bullet it
        appears in -- found live (2026-09-27) consolidating this into
        DiffGenerator.generate_diff, which previously used a separate,
        weaker check with its own cross-bullet dedup; calling this method
        once per bullet pair without sharing dedup state reintroduced the
        exact per-bullet-repetition problem that separate check's dedup
        existed to prevent. Defaults to a fresh set (today's per-call
        behavior, unchanged for every other existing caller).
        """
        if already_reported is None:
            already_reported = set()
        issues = []
        trusted_blob = self._profile_blob(profile) + " " + original.lower()
        new_lower = new.lower()

        for metric in self._METRIC_PATTERN.findall(new):
            key = f"metric:{metric.lower()}"
            if key in already_reported:
                continue
            if metric.lower() not in trusted_blob and metric not in trusted_blob:
                issues.append(
                    f"⚠️ FABRICATION RISK: metric '{metric}' mentioned in '{new}' "
                    "but not in the original bullet or profile"
                )
                already_reported.add(key)

        for tech in self._TECH_KEYWORDS:
            # Same "word:" key namespace as the generalized new-word check
            # below -- found live (2026-09-27): a separate "tech:" namespace
            # let the same term (e.g. "kubernetes") get flagged twice, once
            # by each check, since neither recognized the other's dedup key.
            key = f"word:{self._stem(tech)}"
            if key in already_reported:
                continue
            pattern = self._tech_pattern(tech)
            if re.search(pattern, new_lower) and not re.search(pattern, trusted_blob):
                issues.append(
                    f"⚠️ FABRICATION RISK: '{tech}' mentioned in '{new}' but not in the original bullet or profile"
                )
                already_reported.add(key)

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
        competency_backed_words = self._competency_label_words_evidenced_by(original)
        safe_stems = {self._stem(w) for w in self._SAFE_REPHRASE_WORDS} | {
            self._stem(w) for w in competency_backed_words
        }
        genuinely_new = {
            w for w in self._content_words(new)
            if self._stem(w) not in trusted_stems
            and self._stem(w) not in original_stems
            and self._stem(w) not in safe_stems
            and f"word:{self._stem(w)}" not in already_reported
        }
        if genuinely_new:
            issues.append(
                f"⚠️ POSSIBLY UNVERIFIED: new term(s) {sorted(genuinely_new)} in '{new}' "
                "not grounded in the original bullet or profile -- review before using"
            )
            for w in genuinely_new:
                already_reported.add(f"word:{self._stem(w)}")

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
