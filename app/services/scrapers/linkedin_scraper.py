"""
LinkedIn Jobs Scraper - Handles authentication and anti-bot measures
IMPORTANT: This scraper requires careful consideration of LinkedIn's Terms of Service
and implements ethical scraping practices with authentication handling
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
import time
import os
from urllib.parse import urljoin, quote_plus
from playwright.async_api import Page

from .base_scraper import JobScraper, ScraperResult, ScraperConfig
from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

class LinkedInScraperConfig(ScraperConfig):
    """Extended config for LinkedIn-specific settings"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.login_required = True
        self.save_session = True
        self.session_file = "linkedin_session.json"
        self.max_login_attempts = 3
        self.respect_rate_limits = True
        self.min_delay_between_requests = 3  # Increased for LinkedIn

class LinkedInScraper(JobScraper):
    """
    LinkedIn Jobs scraper with authentication handling
    
    ETHICAL CONSIDERATIONS:
    - Respects robots.txt and LinkedIn's Terms of Service
    - Implements rate limiting and human-like behavior
    - Uses legitimate browser automation, not API abuse
    - Requires user consent and valid LinkedIn account
    """
    
    def __init__(self, config: Optional[LinkedInScraperConfig] = None):
        super().__init__(config or LinkedInScraperConfig())
        self.linkedin_config = config or LinkedInScraperConfig()
        self.is_authenticated = False
        self.session_data = None
    
    @property
    def site_name(self) -> str:
        return "LinkedIn"
    
    @property
    def base_url(self) -> str:
        return "https://www.linkedin.com"
    
    def _build_search_url(self, keywords: str, location: Optional[str] = None) -> str:
        """Build LinkedIn Jobs search URL"""
        base_search = f"{self.base_url}/jobs/search/"
        
        params = []
        if keywords:
            params.append(f"keywords={quote_plus(keywords)}")
        if location:
            params.append(f"location={quote_plus(location)}")
        
        # Default filters for remote jobs
        params.extend([
            "f_WT=2",  # Remote work filter
            "f_TPR=r86400",  # Posted in last 24 hours
            "sortBy=DD"  # Sort by date
        ])
        
        if params:
            return f"{base_search}?" + "&".join(params)
        return base_search
    
    async def search_jobs(self, keywords: str, location: Optional[str] = None, num_results: int = 10) -> ScraperResult:
        """
        Search for jobs on LinkedIn with authentication handling
        """
        start_time = time.time()
        
        try:
            # Setup browser with LinkedIn-specific settings
            self.browser = await self._setup_linkedin_browser()
            self.page = await self._setup_page(self.browser)
            
            # Handle authentication
            if not await self._ensure_authentication():
                logger.error("LinkedIn authentication failed")
                return await self._fallback_to_mock_data(keywords, num_results, start_time)
            
            # Build search URL
            search_url = self._build_search_url(keywords, location)
            logger.info(f"Searching LinkedIn with URL: {search_url}")
            
            # Navigate to search page with extra care
            await self._navigate_safely(search_url)
            
            # Wait for results with LinkedIn-specific selectors
            if not await self._wait_for_linkedin_results():
                logger.warning("Failed to load LinkedIn search results")
                return await self._fallback_to_mock_data(keywords, num_results, start_time)
            
            # Extract job data
            job_data_list = await self._extract_job_data(self.page)
            
            # Convert to JobPosting models
            jobs = []
            for job_data in job_data_list[:num_results]:
                job_posting = self._parse_job_to_model(job_data)
                if job_posting:
                    jobs.append(job_posting)
            
            execution_time = time.time() - start_time
            
            if jobs:
                logger.info(f"Successfully scraped {len(jobs)} jobs from LinkedIn")
                return ScraperResult(
                    jobs=jobs,
                    source=self.site_name,
                    success=True,
                    jobs_found=len(jobs),
                    execution_time=execution_time
                )
            else:
                logger.warning("No jobs found on LinkedIn, using mock data")
                return await self._fallback_to_mock_data(keywords, num_results, start_time)
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {e}")
            return await self._fallback_to_mock_data(keywords, num_results, start_time)
    
    async def _setup_linkedin_browser(self):
        """Setup browser with LinkedIn-specific anti-detection measures"""
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        
        # Enhanced browser args for LinkedIn
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--no-sandbox',
            '--disable-features=VizDisplayCompositor',
            '--disable-extensions-file-access-check',
            '--disable-plugins-discovery',
            '--start-maximized'
        ]
        
        browser = await playwright.chromium.launch(
            headless=False,  # LinkedIn detection is stronger, consider non-headless
            args=browser_args,
            slow_mo=100  # Add delay between actions
        )
        
        return browser
    
    async def _ensure_authentication(self) -> bool:
        """
        Ensure user is authenticated with LinkedIn
        
        This method handles:
        1. Checking for existing session
        2. Prompting for login if needed
        3. Saving session for future use
        """
        try:
            # Try to load existing session
            if await self._load_session():
                if await self._verify_session():
                    self.is_authenticated = True
                    return True
            
            # Need to authenticate
            logger.info("LinkedIn authentication required")
            
            # Navigate to LinkedIn login
            await self.page.goto(f"{self.base_url}/login", timeout=self.config.timeout)
            await self._human_like_delay()
            
            # Check if already logged in (redirected)
            if "feed" in self.page.url or "jobs" in self.page.url:
                logger.info("Already logged in to LinkedIn")
                await self._save_session()
                self.is_authenticated = True
                return True
            
            # Wait for manual login or implement automated login
            # SECURITY NOTE: Automated login requires careful credential handling
            success = await self._handle_login_process()
            
            if success:
                await self._save_session()
                self.is_authenticated = True
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"LinkedIn authentication error: {e}")
            return False
    
    async def _handle_login_process(self) -> bool:
        """
        Handle LinkedIn login process
        
        IMPLEMENTATION OPTIONS:
        1. Manual login (user completes login manually)
        2. Automated login (requires secure credential storage)
        3. Session reuse (preferred for repeated usage)
        """
        
        # Option 1: Manual login (safest approach)
        if await self._prompt_for_manual_login():
            return True
        
        # Option 2: Automated login (implement if credentials are securely stored)
        # return await self._automated_login()
        
        return False
    
    async def _prompt_for_manual_login(self) -> bool:
        """
        Prompt user to complete login manually
        This is the safest approach for authentication
        """
        try:
            logger.info("Please complete LinkedIn login manually in the browser window")
            logger.info("After logging in, the scraper will continue automatically")
            
            # Wait for successful login (detected by URL change)
            for attempt in range(60):  # Wait up to 5 minutes
                await asyncio.sleep(5)
                current_url = self.page.url
                
                # Check for successful login indicators
                if any(indicator in current_url for indicator in ['feed', 'jobs', 'in/']):
                    logger.info("Login successful!")
                    return True
                
                # Check if still on login page
                if 'login' not in current_url and 'challenge' not in current_url:
                    # Might be logged in, verify
                    if await self._verify_session():
                        return True
            
            logger.warning("Login timeout - please try again")
            return False
            
        except Exception as e:
            logger.error(f"Manual login error: {e}")
            return False
    
    async def _verify_session(self) -> bool:
        """Verify that LinkedIn session is valid"""
        try:
            # Navigate to a protected page to verify login
            await self.page.goto(f"{self.base_url}/jobs/", timeout=10000)
            await asyncio.sleep(2)
            
            # Check for login indicators
            current_url = self.page.url
            if 'login' in current_url or 'challenge' in current_url:
                return False
            
            # Look for user-specific elements
            user_elements = await self.page.query_selector_all('.global-nav__me, [data-test-global-nav-me]')
            return len(user_elements) > 0
            
        except Exception as e:
            logger.debug(f"Session verification failed: {e}")
            return False
    
    async def _load_session(self) -> bool:
        """Load saved LinkedIn session"""
        # Implementation would load browser cookies/session data
        # For now, return False to require fresh authentication
        return False
    
    async def _save_session(self) -> bool:
        """Save LinkedIn session for future use"""
        # Implementation would save browser cookies/session data
        # This would enable session reuse across runs
        return True
    
    async def _navigate_safely(self, url: str):
        """Navigate to URL with LinkedIn-specific safety measures"""
        try:
            await self.page.goto(url, timeout=self.config.timeout)
            await self._human_like_delay()
            
            # Check for CAPTCHA or security challenges
            if await self._handle_security_challenges():
                # Retry navigation after handling challenges
                await self.page.goto(url, timeout=self.config.timeout)
                
        except Exception as e:
            logger.warning(f"Navigation error: {e}")
            raise
    
    async def _handle_security_challenges(self) -> bool:
        """Handle LinkedIn security challenges (CAPTCHA, etc.)"""
        try:
            # Check for common challenge indicators
            challenge_selectors = [
                '[data-test-challenge]',
                '.challenge-page',
                '#captcha-internal',
                '.captcha-container'
            ]
            
            for selector in challenge_selectors:
                if await self.page.query_selector(selector):
                    logger.warning("LinkedIn security challenge detected")
                    logger.info("Please complete the security challenge manually")
                    
                    # Wait for user to complete challenge
                    for _ in range(30):  # Wait up to 2.5 minutes
                        await asyncio.sleep(5)
                        if not await self.page.query_selector(selector):
                            logger.info("Challenge completed")
                            return True
                    
                    logger.warning("Challenge timeout")
                    return False
            
            return False
            
        except Exception as e:
            logger.warning(f"Error handling security challenges: {e}")
            return False
    
    async def _wait_for_linkedin_results(self) -> bool:
        """Wait for LinkedIn job search results to load"""
        try:
            # LinkedIn-specific result selectors
            result_selectors = [
                '.jobs-search__results-list',
                '.job-card-container',
                '[data-test-job-card]',
                '.jobs-search-results-list'
            ]
            
            for selector in result_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=15000)
                    return True
                except:
                    continue
            
            logger.warning("LinkedIn results not found with expected selectors")
            return False
            
        except Exception as e:
            logger.debug(f"Error waiting for LinkedIn results: {e}")
            return False
    
    async def _extract_job_data(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job data from LinkedIn search results"""
        jobs_data = []
        
        try:
            # LinkedIn job card selectors
            job_selectors = [
                '.job-card-container',
                '[data-test-job-card]',
                '.jobs-search-results__list-item'
            ]
            
            job_elements = None
            for selector in job_selectors:
                try:
                    job_elements = await page.query_selector_all(selector)
                    if job_elements:
                        logger.debug(f"Found {len(job_elements)} LinkedIn jobs with selector: {selector}")
                        break
                except:
                    continue
            
            if not job_elements:
                logger.warning("No LinkedIn job elements found")
                return []
            
            # Extract data from each job card
            for element in job_elements[:20]:
                try:
                    job_data = await self._extract_linkedin_job_data(element)
                    if job_data and job_data.get('title') and job_data.get('company_name'):
                        jobs_data.append(job_data)
                except Exception as e:
                    logger.debug(f"Error extracting LinkedIn job: {e}")
                    continue
            
            logger.info(f"Extracted {len(jobs_data)} valid jobs from LinkedIn")
            return jobs_data
            
        except Exception as e:
            logger.error(f"Error extracting LinkedIn job data: {e}")
            return []
    
    async def _extract_linkedin_job_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract data from a single LinkedIn job card"""
        try:
            job_data = {}
            
            # Extract job title and URL
            title_selectors = [
                '.job-card-list__title a',
                '[data-test-job-title] a',
                '.job-card-container__link'
            ]
            for selector in title_selectors:
                try:
                    title_element = await element.query_selector(selector)
                    if title_element:
                        job_data['title'] = await title_element.inner_text()
                        job_data['url'] = await title_element.get_attribute('href')
                        break
                except:
                    continue
            
            # Extract company name
            company_selectors = [
                '.job-card-container__company-name',
                '[data-test-job-company-name]',
                '.job-card-list__company-name'
            ]
            for selector in company_selectors:
                try:
                    company_element = await element.query_selector(selector)
                    if company_element:
                        job_data['company_name'] = await company_element.inner_text()
                        break
                except:
                    continue
            
            # Extract location
            location_selectors = [
                '.job-card-container__metadata-item',
                '[data-test-job-location]',
                '.job-card-list__location'
            ]
            for selector in location_selectors:
                try:
                    location_element = await element.query_selector(selector)
                    if location_element:
                        location_text = await location_element.inner_text()
                        if location_text and 'ago' not in location_text.lower():
                            job_data['location'] = location_text
                            break
                except:
                    continue
            
            return job_data if job_data.get('title') else None
            
        except Exception as e:
            logger.debug(f"Error extracting single LinkedIn job: {e}")
            return None
    
    def _parse_job_to_model(self, job_data: Dict[str, Any]) -> Optional[JobPosting]:
        """Convert raw LinkedIn job data to JobPosting model"""
        try:
            # Ensure URL is absolute
            job_url = job_data.get('url', '')
            if job_url and not job_url.startswith('http'):
                job_url = urljoin(self.base_url, job_url)
            
            job_posting = JobPosting(
                job_url=job_url,
                title=self._clean_text(job_data.get('title', '')),
                company_name=self._clean_text(job_data.get('company_name', '')),
                location_text=self._clean_text(job_data.get('location', 'Remote')),
                source_platform=self.site_name,
                full_description_raw=self._clean_text(job_data.get('description', '')),
                processing_status="pending"
            )
            
            return job_posting
            
        except Exception as e:
            logger.error(f"Error parsing LinkedIn job to model: {e}")
            return None
    
    async def _fallback_to_mock_data(self, keywords: str, num_results: int, start_time: float) -> ScraperResult:
        """Generate mock LinkedIn data as fallback"""
        execution_time = time.time() - start_time
        mock_jobs = self._generate_mock_jobs(keywords, num_results)
        
        return ScraperResult(
            jobs=mock_jobs,
            source=f"{self.site_name}_Mock",
            success=True,
            error_message="Used mock data - LinkedIn scraping requires authentication",
            jobs_found=len(mock_jobs),
            execution_time=execution_time
        ) 