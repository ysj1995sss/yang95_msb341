"""Job service orchestrator for the job search pipeline.

Coordinates: user goals → scraper selection → scraping → deduplication → database storage.
"""

from datetime import datetime
from typing import List, Optional, Tuple
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.job_search.database import JobDatabase
from resume_tailorer.job_search.deduplicator import JobDeduplicator
from resume_tailorer.job_search.candidate_fit import CandidateFitScorer
from resume_tailorer.job_search.scrapers import (
    LinkedInScraper,
    IndeedScraper,
    HandshakeScraper,
    GreenhouseScraper,
)
from resume_tailorer.models.career_profile import CareerTruthProfile


class JobService:
    """Orchestrates the entire job search pipeline."""

    def __init__(self, db_path: str = "job_search.db"):
        """Initialize JobService with database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db = JobDatabase(db_path=db_path)
        self.db.create_tables()
        self.deduplicator = JobDeduplicator()
        self.fit_scorer = CandidateFitScorer()

        # Mapping of JobSource to scraper classes (initialized here for mockability)
        self.scraper_map = {
            JobSource.LINKEDIN: LinkedInScraper,
            JobSource.INDEED: IndeedScraper,
            JobSource.HANDSHAKE: HandshakeScraper,
            JobSource.GREENHOUSE: GreenhouseScraper,
        }

    def search_and_store(
        self,
        goals: SearchGoals,
        sources: List[JobSource],
        career_profile: Optional[CareerTruthProfile] = None
    ) -> int:
        """Search for jobs and store in database.

        Orchestration logic:
        1. Validate goals (min_salary ≤ max_salary, required fields present)
        2. For each requested source:
           - Instantiate the appropriate scraper
           - Call scraper.scrape(goals) to get postings
           - Collect all results
        3. Deduplicate all collected postings via JobDeduplicator
        4. For each deduplicated posting:
           - Call database.save_job_posting()
           - Increment stored count
        5. Return total count stored

        Args:
            goals: SearchGoals object with search criteria
            sources: List of JobSource enum values to scrape
            career_profile: Optional CareerTruthProfile for fit scoring

        Returns:
            Count of jobs stored in database
        """
        # Step 1: Validate goals
        self._validate_goals(goals)

        # Step 2: Scrape from all sources
        all_postings = []
        for source in sources:
            try:
                scraper = self._get_scraper(source)
                if scraper:
                    postings = scraper.scrape(goals)
                    all_postings.extend(postings)
            except Exception:
                # Graceful error handling - skip this source and continue
                pass

        # Step 3: Deduplicate
        deduplicated_postings = self.deduplicator.deduplicate(all_postings)

        # Step 4 & 5: Store and count
        stored_count = 0
        for posting in deduplicated_postings:
            try:
                self.db.save_job_posting(posting)
                stored_count += 1
            except Exception:
                # Skip jobs that fail to save
                pass

        return stored_count

    def get_available_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Retrieve jobs from database matching search goals.

        Returns results sorted by posted_date descending.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects matching the goals
        """
        jobs = self.db.search_jobs(goals)

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

    def close(self) -> None:
        """Close database connection."""
        if self.db:
            self.db.close()

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

        if not goals.location or not goals.location.strip():
            raise ValueError("location is required")

    def _get_scraper(self, source: JobSource):
        """Get scraper instance for the given source.

        Args:
            source: JobSource enum value

        Returns:
            Scraper instance or None if source not supported
        """
        scraper_class = self.scraper_map.get(source)
        if scraper_class:
            return scraper_class()
        return None
