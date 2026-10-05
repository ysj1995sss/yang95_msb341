"""Job scrapers for multiple platforms."""

from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper
from resume_tailorer.job_search.scrapers.linkedin_scraper import LinkedInScraper
from resume_tailorer.job_search.scrapers.indeed_scraper import IndeedScraper
from resume_tailorer.job_search.scrapers.handshake_scraper import HandshakeScraper
from resume_tailorer.job_search.scrapers.greenhouse_scraper import GreenhouseScraper
from resume_tailorer.job_search.scrapers.lever_scraper import LeverScraper
from resume_tailorer.job_search.scrapers.ashby_scraper import AshbyScraper
from resume_tailorer.job_search.scrapers.smartrecruiters_scraper import SmartRecruitersScraper

__all__ = [
    "BaseScraper",
    "LinkedInScraper",
    "IndeedScraper",
    "HandshakeScraper",
    "GreenhouseScraper",
    "LeverScraper",
    "AshbyScraper",
    "SmartRecruitersScraper",
]
