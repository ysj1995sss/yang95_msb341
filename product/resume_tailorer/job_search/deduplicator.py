"""Job deduplicator for merging duplicate jobs from multiple sources."""

from typing import List, Dict, Tuple
from dataclasses import replace
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.fingerprint import normalize_url
from resume_tailorer.job_search.normalize import (
    normalize_company,
    normalize_location,
    normalize_title,
)


class JobDeduplicator:
    """Merges duplicate jobs scraped from multiple sources."""

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
        """Deduplicate job postings.

        Grouping:
        1. Same normalized URL → same group (always merge).
        2. Else same normalized (company, title, location), but do NOT merge
           two postings from the same source with distinct non-empty source_ids.
           Cross-source matches still merge.
        """
        if not postings:
            return []

        url_groups: Dict[str, List[JobPosting]] = {}
        no_url: List[JobPosting] = []
        for posting in postings:
            url_key = normalize_url(posting.url)
            if url_key:
                url_groups.setdefault(url_key, []).append(posting)
            else:
                no_url.append(posting)

        merged_from_url: List[JobPosting] = [
            self._merge_group(group) for group in url_groups.values()
        ]

        candidates = merged_from_url + no_url
        clusters: List[List[JobPosting]] = []
        # Only postings with the same (company, title, location) can merge, so each one is
        # compared with the clusters under its own key, not every cluster (was quadratic).
        by_key: Dict[Tuple[str, str, str], List[List[JobPosting]]] = {}
        for posting in candidates:
            same_key = by_key.setdefault(self._ct_key(posting), [])
            for cluster in same_key:
                if self._can_join_cluster(posting, cluster):
                    cluster.append(posting)
                    break
            else:
                cluster = [posting]
                clusters.append(cluster)
                same_key.append(cluster)

        return [self._merge_group(cluster) for cluster in clusters]

    def _ct_key(self, posting: JobPosting) -> Tuple[str, str, str]:
        return (
            normalize_company(posting.company),
            normalize_title(posting.title),
            normalize_location(posting.location),
        )

    def _can_join_cluster(self, posting: JobPosting, cluster: List[JobPosting]) -> bool:
        if not cluster:
            return True
        if self._ct_key(posting) != self._ct_key(cluster[0]):
            return False

        posting_url = normalize_url(posting.url)
        if posting_url:
            for member in cluster:
                if normalize_url(member.url) == posting_url:
                    return True

        posting_sid = (posting.source_id or "").strip()
        for member in cluster:
            member_sid = (member.source_id or "").strip()
            if (
                posting.source == member.source
                and posting_sid
                and member_sid
                and posting_sid != member_sid
            ):
                return False
        return True

    def _merge_group(self, group: List[JobPosting]) -> JobPosting:
        best_posting = self._select_best_posting(group)
        alternative_urls = []
        for posting in group:
            if posting is not best_posting and posting.url:
                if posting.url not in alternative_urls and posting.url != best_posting.url:
                    alternative_urls.append(posting.url)
        return replace(best_posting, alternative_sources=alternative_urls)

    def _select_best_posting(self, group: List[JobPosting]) -> JobPosting:
        if not group:
            return None

        def get_priority(posting: JobPosting) -> int:
            return self.SOURCE_PRIORITY.get(posting.source, 0)

        return max(group, key=get_priority)
