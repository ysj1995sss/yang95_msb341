"""Job service orchestrator for the job search pipeline.

Coordinates: user goals → scraper selection → scraping → deduplication → database storage.
"""

from dataclasses import replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from resume_tailorer.job_search.models import (
    SearchGoals,
    JobPosting,
    JobSource,
    FitResult,
    ProviderRunResult,
    ProviderRunStatus,
    SearchRunStatus,
    SearchRunSummary,
)
from resume_tailorer.job_search.database import JobDatabase
from resume_tailorer.job_search.job_attributes import apply_goal_filters
from resume_tailorer.job_search.deduplicator import JobDeduplicator
from resume_tailorer.job_search.candidate_fit import CandidateFitScorer
from resume_tailorer.job_search.scrapers import (
    LinkedInScraper,
    IndeedScraper,
    HandshakeScraper,
    GreenhouseScraper,
)
from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import ApplicationMode, ApplicationSubmission
from resume_tailorer.applications.submission_engine import SubmissionEngine

PENDING_TAILOR_JOB_KEY = "pending_tailor_job"


def _profile_hash(profile: CareerTruthProfile) -> str:
    """Content hash of a profile snapshot -- same canonical-JSON-then-sha256
    approach as apps/api's profile_snapshot_hash (Steps 16-20), so an
    application record can show whether the candidate's profile has
    changed since they applied, without storing the whole profile twice."""
    import dataclasses
    import hashlib
    import json

    canonical = json.dumps(dataclasses.asdict(profile), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_tailor_snapshot(
    job: JobPosting,
    fit: FitResult | None = None,
    *,
    selected_at: datetime | None = None,
) -> Dict[str, Any]:
    """Build the APPLY → Step 10 handoff payload (job + fit snapshot)."""
    job_id = f"{job.source.value}_{job.source_id}"
    fit_dict = fit.to_dict() if fit is not None else {}
    return {
        "job_id": job_id,
        "title": job.title,
        "company": job.company,
        "description": job.description or "",
        "url": job.url or "",
        "candidate_fit": fit_dict,
        "selected_at": (selected_at or datetime.now()).isoformat(),
    }


class JobService:
    """Orchestrates the entire job search pipeline."""

    def __init__(self, db_path: str = "job_search.db", applications_db_path: str = "applications.db"):
        """Initialize JobService with database.

        Args:
            db_path: Path to SQLite database file for job postings.
            applications_db_path: Path to SQLite database file for
                application submissions and status tracking.
        """
        self.db = JobDatabase(db_path=db_path)
        self.db.create_tables()
        self.deduplicator = JobDeduplicator()
        self.fit_scorer = CandidateFitScorer()

        self.applications_db = ApplicationDatabase(db_path=applications_db_path)
        self.applications_db.create_tables()
        self._submission_engine = SubmissionEngine(self.applications_db)

        # Mapping of JobSource to scraper classes (initialized here for mockability)
        self.scraper_map = {
            JobSource.LINKEDIN: LinkedInScraper,
            JobSource.INDEED: IndeedScraper,
            JobSource.HANDSHAKE: HandshakeScraper,
            JobSource.GREENHOUSE: GreenhouseScraper,
        }

        # Cache of instantiated scrapers, keyed by JobSource. This ensures the
        # SAME scraper instance used during search_and_store() is the one
        # returned by later _get_scraper() calls (e.g. from the UI, to inspect
        # the instance's data_source after a scrape), instead of a fresh,
        # never-scraped instance whose data_source is always None.
        self._scraper_cache = {}
        self.last_search_run: Optional[SearchRunSummary] = None

    def search_and_store(
        self,
        goals: SearchGoals,
        sources: List[JobSource]
    ) -> SearchRunSummary:
        """Search for jobs and store in database.

        Orchestration logic:
        1. Validate goals (min_salary ≤ max_salary, required fields present)
        2. For each requested source (isolated — one failure does not abort others):
           - Instantiate the appropriate scraper
           - Call scraper.scrape(goals) to get postings
           - Record ProviderRunResult (ok / failed / skipped)
        3. Deduplicate all collected postings via JobDeduplicator
        4. For each remaining posting:
           - Call database.save_job_posting()
           - Increment stored count
        5. Return SearchRunSummary (observability + total_stored)

        Args:
            goals: SearchGoals object with search criteria
            sources: List of JobSource enum values to scrape

        Returns:
            SearchRunSummary with per-provider outcomes and totals
        """
        started = datetime.now()
        self._validate_goals(goals)

        all_postings: List[JobPosting] = []
        provider_results: List[ProviderRunResult] = []

        for source in sources:
            scraper = self._get_scraper(source)
            if scraper is None:
                provider_results.append(
                    ProviderRunResult(
                        source=source,
                        status=ProviderRunStatus.SKIPPED,
                        scraped=0,
                        error="No scraper configured for this source",
                    )
                )
                continue
            try:
                postings = scraper.scrape(goals)
                if getattr(scraper, "data_source", None) == "unavailable":
                    raise ConnectionError("Source could not be reached")
                batch = list(postings or [])
                all_postings.extend(batch)
                provider_results.append(
                    ProviderRunResult(
                        source=source,
                        status=ProviderRunStatus.OK,
                        scraped=len(batch),
                    )
                )
            except Exception as exc:
                provider_results.append(
                    ProviderRunResult(
                        source=source,
                        status=ProviderRunStatus.FAILED,
                        scraped=0,
                        error=str(exc) or exc.__class__.__name__,
                    )
                )

        deduplicated_postings = self.deduplicator.deduplicate(all_postings)
        total_after_dedupe = len(deduplicated_postings)

        stored_count = 0
        for posting in deduplicated_postings:
            try:
                self.db.save_job_posting(posting)
                stored_count += 1
            except Exception:
                pass

        ok_count = sum(1 for p in provider_results if p.status == ProviderRunStatus.OK)
        fail_count = sum(1 for p in provider_results if p.status == ProviderRunStatus.FAILED)
        if fail_count == 0 and ok_count > 0:
            run_status = SearchRunStatus.OK
        elif ok_count > 0 and fail_count > 0:
            run_status = SearchRunStatus.PARTIAL
        elif ok_count == 0 and fail_count > 0:
            run_status = SearchRunStatus.FAILED
        else:
            # All skipped or empty source list after validation
            run_status = SearchRunStatus.FAILED if sources else SearchRunStatus.OK

        summary = SearchRunSummary(
            started_at=started,
            finished_at=datetime.now(),
            providers=provider_results,
            total_scraped=len(all_postings),
            total_after_dedupe=total_after_dedupe,
            total_stored=stored_count,
            status=run_status,
        )
        self.last_search_run = summary
        return summary

    def get_available_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Retrieve jobs from database matching search goals.

        Returns results sorted by posted_date descending.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects matching the goals
        """
        # Title matching happens in apply_goal_filters (word-based, same rule
        # the scraper uses), not as a SQL substring match.
        jobs = apply_goal_filters(self.db.search_jobs(replace(goals, job_title="")), goals)

        # Sort by posted_date descending (most recent first)
        jobs.sort(
            key=lambda j: j.posted_date if j.posted_date else datetime.min,
            reverse=True
        )

        return jobs

    def get_job_with_fit_score(
        self,
        job_id: str,
        profile: CareerTruthProfile
    ) -> Optional[Tuple[JobPosting, float]]:
        """Retrieve job and calculate fit score.

        Args:
            job_id: Job ID in format "{source}_{source_id}"
            profile: CareerTruthProfile for scoring

        Returns:
            Optional[Tuple[JobPosting, float]]: Tuple of (JobPosting, fit_score),
            or None if no job matches job_id.
        """
        job = self.db.get_job_posting(job_id)
        if job is None:
            return None

        fit_score = self.fit_scorer.score_fit(profile, job)
        return (job, fit_score)

    def apply_for_job(
        self,
        job_id: str,
        profile: CareerTruthProfile,
        resume_pdf_path: str,
        mode: ApplicationMode,
        resume_match_score: float,
        dry_run: bool = True,
    ) -> ApplicationSubmission:
        """
        Submit (or dry-run) an application for a stored job posting.

        Orchestrates: fetch job from DB -> compute candidate fit score ->
        delegate to SubmissionEngine (parse form -> fill -> optionally
        submit -> record).

        Args:
            job_id: Job ID in format "{source}_{source_id}".
            profile: The candidate's verified career data.
            resume_pdf_path: Path to the tailored resume PDF used for
                this application.
            mode: MANUAL, ASSIST, or AUTO.
            resume_match_score: Resume Match score from Sprint 1's
                ResumeBenchmarker for this job (JobService does not
                compute this itself — it's a separate module's output,
                passed in by the caller).
            dry_run: If True (default), never performs a real network
                submission. See SubmissionEngine for the full safety
                model.

        Returns:
            The recorded ApplicationSubmission.

        Raises:
            ValueError: If job_id is not found, or if the underlying
                SubmissionEngine refuses to submit (unsupported platform,
                or Auto mode with an unfilled required field).
        """
        job = self.db.get_job_posting(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        fit_detail = self.fit_scorer.score_fit_detailed(profile, job)
        candidate_fit_score = fit_detail.overall_fit if fit_detail.overall_fit is not None else 80.0

        # Immutable snapshots (spec 003 Step 22): the dashboard must be able
        # to show what was true when the user applied, not whatever the
        # live job posting or fit score look like now -- same principle as
        # TailoringRun.profile_snapshot_json from Steps 16-20.
        job_snapshot = {
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "url": job.url or "",
            "ats_platform": job.ats_platform or "",
            "work_mode": job.work_mode,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
        }
        candidate_fit_snapshot = fit_detail.to_dict()

        return self._submission_engine.apply_for_job(
            job_posting_id=job_id,
            form_url=job.url,
            ats_platform=job.ats_platform.lower() if job.ats_platform else "",
            profile=profile,
            resume_pdf_path=resume_pdf_path,
            job_snapshot=job_snapshot,
            candidate_fit_snapshot=candidate_fit_snapshot,
            career_profile_version=_profile_hash(profile),
            candidate_fit_score=candidate_fit_score,
            resume_match_score=resume_match_score,
            mode=mode,
            dry_run=dry_run,
        )

    def close(self) -> None:
        """Close database connections."""
        if self.db:
            self.db.close()
        if self.applications_db:
            self.applications_db.close()

    def _validate_goals(self, goals: SearchGoals) -> None:
        """Validate search goals.

        Raises:
            ValueError: If goals are invalid
        """
        # Check min_salary <= max_salary (SearchGoals __post_init__ handles this)
        if goals.min_salary > goals.max_salary:
            raise ValueError(
                f"min_salary ({goals.min_salary}) must be <= max_salary ({goals.max_salary})"
            )

        # Check required fields
        if not goals.job_title or not goals.job_title.strip():
            raise ValueError("job_title is required")

    def _get_scraper(self, source: JobSource):
        """Get scraper instance for the given source.

        Args:
            source: JobSource enum value

        Returns:
            Scraper instance or None if source not supported
        """
        if source in self._scraper_cache:
            return self._scraper_cache[source]

        scraper_class = self.scraper_map.get(source)
        if scraper_class:
            scraper = scraper_class()
            self._scraper_cache[source] = scraper
            return scraper
        return None
