"""Job scrapers for multiple platforms."""

from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper
from resume_tailorer.job_search.scrapers.linkedin_scraper import LinkedInScraper
from resume_tailorer.job_search.scrapers.indeed_scraper import IndeedScraper
from resume_tailorer.job_search.scrapers.handshake_scraper import HandshakeScraper
from resume_tailorer.job_search.scrapers.greenhouse_scraper import GreenhouseScraper

__all__ = [
    "BaseScraper",
    "LinkedInScraper",
    "IndeedScraper",
    "HandshakeScraper",
    "GreenhouseScraper",
]
