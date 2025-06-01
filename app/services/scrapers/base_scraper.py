"""
Base Job Scraper - Abstract interface for all job site scrapers
Provides common functionality and enforces consistent scraper behavior
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
import time
import random
import asyncio
from playwright.async_api import async_playwright, Browser, Page
from fake_useragent import UserAgent

from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

@dataclass
class ScraperConfig:
    """Configuration for scraper behavior"""
    max_results: int = 10
    delay_range: tuple = (2, 5)  # Random delay between requests (seconds)
    timeout: int = 30000  # Page timeout in milliseconds
    headless: bool = True
    user_agent_rotation: bool = True
    respect_robots_txt: bool = True
    max_retries: int = 3

@dataclass
class ScraperResult:
    """Result from a scraper operation"""
    jobs: List[JobPosting]
    source: str
    success: bool
    error_message: Optional[str] = None
    jobs_found: int = 0
    execution_time: float = 0.0

class JobScraper(ABC):
    """
    Abstract base class for all job site scrapers.
    Enforces consistent interface and provides common functionality.
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.user_agent = UserAgent() if self.config.user_agent_rotation else None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    @property
    @abstractmethod
    def site_name(self) -> str:
        """Name of the job site (e.g., 'LinkedIn', 'Indeed')"""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the job site"""
        pass
    
    @abstractmethod
    async def search_jobs(self, keywords: str, location: Optional[str] = None, num_results: int = 10) -> ScraperResult:
        """
        Search for jobs on the platform.
        
        Args:
            keywords: Job search keywords
            location: Location filter (optional)
            num_results: Maximum number of results to return
            
        Returns:
            ScraperResult with found jobs and metadata
        """
        pass
    
    @abstractmethod
    def _build_search_url(self, keywords: str, location: Optional[str] = None) -> str:
        """Build search URL for the specific platform"""
        pass
    
    @abstractmethod
    async def _extract_job_data(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job data from search results page"""
        pass
    
    @abstractmethod
    def _parse_job_to_model(self, job_data: Dict[str, Any]) -> Optional[JobPosting]:
        """Convert raw job data to JobPosting model"""
        pass
    
    async def _setup_browser(self) -> Browser:
        """Initialize browser with anti-detection measures"""
        playwright = await async_playwright().start()
        
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--no-sandbox',
            '--disable-features=VizDisplayCompositor'
        ]
        
        browser = await playwright.chromium.launch(
            headless=self.config.headless,
            args=browser_args
        )
        
        return browser
    
    async def _setup_page(self, browser: Browser) -> Page:
        """Setup page with realistic user behavior simulation"""
        # Create context with user agent if available
        context_options = {
            'viewport': {'width': 1366, 'height': 768}
        }
        
        if self.user_agent:
            context_options['user_agent'] = self.user_agent.random
        
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        
        # Add realistic headers
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        return page
    
    async def _human_like_delay(self):
        """Add random delay to simulate human behavior"""
        min_delay, max_delay = self.config.delay_range
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def _safe_click(self, page: Page, selector: str) -> bool:
        """Safely click an element with error handling"""
        try:
            await page.click(selector, timeout=5000)
            await self._human_like_delay()
            return True
        except Exception as e:
            logger.warning(f"Failed to click {selector}: {e}")
            return False
    
    async def _safe_fill(self, page: Page, selector: str, text: str) -> bool:
        """Safely fill a form field with error handling"""
        try:
            await page.fill(selector, text, timeout=5000)
            await self._human_like_delay()
            return True
        except Exception as e:
            logger.warning(f"Failed to fill {selector}: {e}")
            return False
    
    async def _wait_for_results(self, page: Page, timeout: int = 10000) -> bool:
        """Wait for search results to load"""
        try:
            # This should be overridden by specific scrapers with their result selectors
            await page.wait_for_load_state('networkidle', timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"Timeout waiting for results: {e}")
            return False
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        return ' '.join(text.strip().split())
    
    def _generate_mock_jobs(self, keywords: str, num_results: int) -> List[JobPosting]:
        """Generate mock jobs as fallback (for testing/development)"""
        mock_jobs = []
        for i in range(min(num_results, 3)):  # Limit mock jobs
            mock_job = JobPosting(
                job_url=f"https://mock-{self.site_name.lower()}.com/job/{i+1}",
                title=f"Mock {keywords} Position {i+1}",
                company_name=f"Mock Company {i+1}",
                location_text="Remote",
                source_platform=f"Mock_{self.site_name}",
                full_description_raw=f"Mock job description for {keywords} position at {self.site_name}. This is a test job posting.",
                processing_status="pending"
            )
            mock_jobs.append(mock_job)
        
        logger.info(f"Generated {len(mock_jobs)} mock jobs for {self.site_name}")
        return mock_jobs
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

import asyncio 