"""Job deduplicator for merging duplicate jobs from multiple sources."""

from typing import List, Dict, Tuple
from dataclasses import replace
from resume_tailorer.job_search.models import JobPosting, JobSource


class JobDeduplicator:
    """Merges duplicate jobs scraped from multiple sources."""

    # Source priority order (higher index = higher priority)
    SOURCE_PRIORITY = {
        JobSource.COMPANY_PAGES: 5,
        JobSource.GREENHOUSE: 5,
        JobSource.LINKEDIN: 4,
        JobSource.INDEED: 3,
        JobSource.HANDSHAKE: 2,
        JobSource.MONSTER: 2,
        JobSource.LEVER: 2,
        JobSource.ASHBY: 2,
        JobSource.WORKDAY: 1,
    }

    def deduplicate(self, postings: List[JobPosting]) -> List[JobPosting]:
        """
        Deduplicate job postings by grouping on (company, title, location).

        For each group, selects the best source based on priority order,
        and merges all alternative URLs into the selected posting.

        Args:
            postings: List of JobPosting objects from multiple sources

        Returns:
            List of deduplicated JobPosting objects with alternative_sources filled
        """
        if not postings:
            return []

        # Group postings by (company, title, location)
        groups: Dict[Tuple[str, str, str], List[JobPosting]] = {}
        for posting in postings:
            key = (posting.company, posting.title, posting.location)
            if key not in groups:
                groups[key] = []
            groups[key].append(posting)

        # Process each group
        result = []
        for group in groups.values():
            # Select the best posting from the group
            best_posting = self._select_best_posting(group)

            # Collect alternative URLs from other sources in the group
            alternative_urls = []
            for posting in group:
                if posting is not best_posting and posting.url:
                    alternative_urls.append(posting.url)

            # Create new posting with alternative sources
            deduplicated_posting = replace(
                best_posting,
                alternative_sources=alternative_urls
            )
            result.append(deduplicated_posting)

        return result

    def _select_best_posting(self, group: List[JobPosting]) -> JobPosting:
        """
        Select the best posting from a group based on source priority.

        Priority order:
        1. Employer career page / Greenhouse (highest)
        2. LinkedIn
        3. Indeed
        4. Handshake, Monster, Lever, Ashby
        5. Other sources (lowest)

        Args:
            group: List of JobPosting objects with same (company, title, location)

        Returns:
            JobPosting object from the highest priority source
        """
        if not group:
            return None

        # Sort by priority (descending) and return the first one
        def get_priority(posting: JobPosting) -> int:
            return self.SOURCE_PRIORITY.get(posting.source, 0)

        best = max(group, key=get_priority)
        return best
