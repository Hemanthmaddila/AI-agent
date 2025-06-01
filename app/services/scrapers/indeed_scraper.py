"""
Indeed Job Scraper - Handles dynamic content and aggregated job sources
Addresses Indeed's specific challenges including pagination and source variations
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
import time
from urllib.parse import urljoin, quote_plus
from playwright.async_api import Page

from .base_scraper import JobScraper, ScraperResult, ScraperConfig
from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

class IndeedScraper(JobScraper):
    """
    Indeed job scraper with enhanced dynamic content handling
    
    CHALLENGES ADDRESSED:
    - Dynamic content loading and AJAX requests
    - Aggregated job sources (external redirects)
    - Anti-scraping measures and rate limiting
    - Variable page structures and A/B testing
    """
    
    @property
    def site_name(self) -> str:
        return "Indeed"
    
    @property
    def base_url(self) -> str:
        return "https://www.indeed.com"
    
    def _build_search_url(self, keywords: str, location: Optional[str] = None) -> str:
        """Build Indeed search URL with proper parameters"""
        base_search = f"{self.base_url}/jobs"
        
        params = []
        if keywords:
            params.append(f"q={quote_plus(keywords)}")
        if location:
            params.append(f"l={quote_plus(location)}")
        else:
            params.append("l=Remote")  # Default to remote jobs
        
        # Additional Indeed-specific parameters
        params.extend([
            "sort=date",  # Sort by date
            "fromage=1",  # Jobs posted in last day
            "radius=0"    # Exact location match
        ])
        
        if params:
            return f"{base_search}?" + "&".join(params)
        return base_search
    
    async def search_jobs(self, keywords: str, location: Optional[str] = None, num_results: int = 10) -> ScraperResult:
        """
        Search for jobs on Indeed with dynamic content handling
        """
        start_time = time.time()
        
        try:
            # Setup browser with Indeed-specific settings
            self.browser = await self._setup_indeed_browser()
            self.page = await self._setup_page(self.browser)
            
            # Build search URL
            search_url = self._build_search_url(keywords, location)
            logger.info(f"Searching Indeed with URL: {search_url}")
            
            # Navigate to search page with Indeed-specific handling
            await self._navigate_to_indeed_search(search_url)
            
            # Handle potential bot detection
            if await self._handle_indeed_challenges():
                logger.info("Successfully handled Indeed challenges")
            
            # Wait for dynamic content to load
            if not await self._wait_for_indeed_results():
                logger.warning("Failed to load Indeed search results")
                return await self._fallback_to_mock_data(keywords, num_results, start_time)
            
            # Extract job data with pagination support
            job_data_list = await self._extract_job_data_with_pagination(num_results)
            
            # Convert to JobPosting models
            jobs = []
            for job_data in job_data_list[:num_results]:
                job_posting = self._parse_job_to_model(job_data)
                if job_posting:
                    jobs.append(job_posting)
            
            execution_time = time.time() - start_time
            
            if jobs:
                logger.info(f"Successfully scraped {len(jobs)} jobs from Indeed")
                return ScraperResult(
                    jobs=jobs,
                    source=self.site_name,
                    success=True,
                    jobs_found=len(jobs),
                    execution_time=execution_time
                )
            else:
                logger.warning("No jobs found on Indeed, using mock data")
                return await self._fallback_to_mock_data(keywords, num_results, start_time)
            
        except Exception as e:
            logger.error(f"Error scraping Indeed: {e}")
            return await self._fallback_to_mock_data(keywords, num_results, start_time)
    
    async def _setup_indeed_browser(self):
        """Setup browser with Indeed-specific anti-detection measures"""
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        
        # Indeed-optimized browser args
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--no-sandbox',
            '--disable-features=VizDisplayCompositor',
            '--disable-extensions-file-access-check',
            '--disable-plugins-discovery',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ]
        
        browser = await playwright.chromium.launch(
            headless=self.config.headless,
            args=browser_args
        )
        
        return browser
    
    async def _navigate_to_indeed_search(self, url: str):
        """Navigate to Indeed search with specific handling"""
        try:
            # Set Indeed-specific headers
            await self.page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Navigate with increased timeout for Indeed
            await self.page.goto(url, timeout=45000, wait_until='domcontentloaded')
            await self._human_like_delay()
            
        except Exception as e:
            logger.warning(f"Navigation to Indeed failed: {e}")
            raise
    
    async def _handle_indeed_challenges(self) -> bool:
        """Handle Indeed's bot detection and challenges"""
        try:
            # Check for common Indeed challenge indicators
            challenge_indicators = [
                'blocked',
                'captcha',
                'verification',
                'robot',
                'suspicious'
            ]
            
            page_content = await self.page.content()
            page_url = self.page.url
            
            # Check page content for challenge indicators
            if any(indicator in page_content.lower() for indicator in challenge_indicators):
                logger.warning("Indeed challenge detected in page content")
                
                # Look for CAPTCHA or verification elements
                captcha_selectors = [
                    '[data-testid="captcha"]',
                    '.captcha-container',
                    '#captcha',
                    '[aria-label*="captcha"]'
                ]
                
                for selector in captcha_selectors:
                    if await self.page.query_selector(selector):
                        logger.info("CAPTCHA detected - please complete manually")
                        
                        # Wait for user to complete CAPTCHA
                        for _ in range(24):  # Wait up to 2 minutes
                            await asyncio.sleep(5)
                            if not await self.page.query_selector(selector):
                                logger.info("CAPTCHA completed successfully")
                                return True
                        
                        logger.warning("CAPTCHA timeout")
                        return False
            
            # Check for redirect to blocked page
            if 'blocked' in page_url or 'captcha' in page_url:
                logger.warning("Redirected to Indeed blocked page")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error handling Indeed challenges: {e}")
            return False
    
    async def _wait_for_indeed_results(self) -> bool:
        """Wait for Indeed search results to load"""
        try:
            # Indeed uses different selectors for job results
            result_selectors = [
                '[data-testid="job-card"]',
                '.job_seen_beacon',
                '.jobsearch-SerpJobCard',
                '.jobsearch-ResultCard',
                '[data-jk]',
                '.slider_container .slider_item'
            ]
            
            # Try each selector with reasonable timeout
            for selector in result_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=15000)
                    logger.debug(f"Found Indeed results with selector: {selector}")
                    return True
                except:
                    continue
            
            # Fallback: check for "no results" message
            no_results_selectors = [
                '[data-testid="no-results"]',
                '.jobsearch-NoResult',
                '#searchform-no-results'
            ]
            
            for selector in no_results_selectors:
                if await self.page.query_selector(selector):
                    logger.info("Indeed returned no results")
                    return True
            
            logger.warning("Indeed results not found with any selector")
            return False
            
        except Exception as e:
            logger.debug(f"Error waiting for Indeed results: {e}")
            return False
    
    async def _extract_job_data_with_pagination(self, max_results: int) -> List[Dict[str, Any]]:
        """Extract job data with pagination support"""
        all_jobs = []
        page_num = 1
        
        while len(all_jobs) < max_results and page_num <= 3:  # Limit to 3 pages
            try:
                logger.debug(f"Extracting jobs from Indeed page {page_num}")
                
                # Extract jobs from current page
                page_jobs = await self._extract_job_data(self.page)
                
                if not page_jobs:
                    logger.debug(f"No jobs found on page {page_num}")
                    break
                
                all_jobs.extend(page_jobs)
                logger.debug(f"Found {len(page_jobs)} jobs on page {page_num}, total: {len(all_jobs)}")
                
                # Check if we have enough jobs
                if len(all_jobs) >= max_results:
                    break
                
                # Try to navigate to next page
                if not await self._navigate_to_next_page():
                    logger.debug("No more pages available")
                    break
                
                page_num += 1
                await self._human_like_delay()
                
            except Exception as e:
                logger.warning(f"Error extracting from page {page_num}: {e}")
                break
        
        logger.info(f"Extracted total of {len(all_jobs)} jobs from {page_num} Indeed pages")
        return all_jobs
    
    async def _navigate_to_next_page(self) -> bool:
        """Navigate to the next page of Indeed results"""
        try:
            # Look for next page link
            next_selectors = [
                '[aria-label="Next Page"]',
                '[data-testid="pagination-page-next"]',
                'a[aria-label="Next"]',
                '.pn:last-child'
            ]
            
            for selector in next_selectors:
                try:
                    next_element = await self.page.query_selector(selector)
                    if next_element:
                        # Check if link is enabled
                        is_disabled = await next_element.get_attribute('aria-disabled')
                        if is_disabled == 'true':
                            return False
                        
                        await next_element.click()
                        await self._human_like_delay()
                        
                        # Wait for new page to load
                        await self.page.wait_for_load_state('domcontentloaded', timeout=15000)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error navigating to next page: {e}")
            return False
    
    async def _extract_job_data(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job data from Indeed search results"""
        jobs_data = []
        
        try:
            # Indeed job card selectors (they change frequently)
            job_selectors = [
                '[data-testid="job-card"]',
                '.job_seen_beacon',
                '.jobsearch-SerpJobCard',
                '.jobsearch-ResultCard',
                '[data-jk]'
            ]
            
            job_elements = None
            for selector in job_selectors:
                try:
                    job_elements = await page.query_selector_all(selector)
                    if job_elements:
                        logger.debug(f"Found {len(job_elements)} Indeed jobs with selector: {selector}")
                        break
                except:
                    continue
            
            if not job_elements:
                logger.warning("No Indeed job elements found")
                return []
            
            # Extract data from each job card
            for element in job_elements:
                try:
                    job_data = await self._extract_indeed_job_data(element)
                    if job_data and job_data.get('title') and job_data.get('company_name'):
                        jobs_data.append(job_data)
                except Exception as e:
                    logger.debug(f"Error extracting Indeed job: {e}")
                    continue
            
            logger.debug(f"Successfully extracted {len(jobs_data)} valid jobs from Indeed page")
            return jobs_data
            
        except Exception as e:
            logger.error(f"Error extracting Indeed job data: {e}")
            return []
    
    async def _extract_indeed_job_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract data from a single Indeed job card"""
        try:
            job_data = {}
            
            # Extract job title and URL
            title_selectors = [
                '[data-testid="job-title"] a',
                '.jobTitle a',
                'h2.jobTitle a',
                '[data-jk] h2 a'
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
                '[data-testid="company-name"]',
                '.companyName',
                '[data-testid="company-name"] a',
                '.companyName a'
            ]
            for selector in company_selectors:
                try:
                    company_element = await element.query_selector(selector)
                    if company_element:
                        company_text = await company_element.inner_text()
                        job_data['company_name'] = company_text
                        break
                except:
                    continue
            
            # Extract location
            location_selectors = [
                '[data-testid="job-location"]',
                '.companyLocation',
                '[data-testid="location"]'
            ]
            for selector in location_selectors:
                try:
                    location_element = await element.query_selector(selector)
                    if location_element:
                        job_data['location'] = await location_element.inner_text()
                        break
                except:
                    continue
            
            # Extract salary if available
            salary_selectors = [
                '[data-testid="salary-snippet"]',
                '.salaryText',
                '.metadata.salary-snippet-container'
            ]
            for selector in salary_selectors:
                try:
                    salary_element = await element.query_selector(selector)
                    if salary_element:
                        job_data['salary'] = await salary_element.inner_text()
                        break
                except:
                    continue
            
            # Extract job snippet/description
            snippet_selectors = [
                '[data-testid="job-snippet"]',
                '.job-snippet',
                '.summary'
            ]
            for selector in snippet_selectors:
                try:
                    snippet_element = await element.query_selector(selector)
                    if snippet_element:
                        snippet_text = await snippet_element.inner_text()
                        if len(snippet_text) > 20:  # Only use substantial snippets
                            job_data['description'] = snippet_text
                            break
                except:
                    continue
            
            return job_data if job_data.get('title') else None
            
        except Exception as e:
            logger.debug(f"Error extracting single Indeed job: {e}")
            return None
    
    def _parse_job_to_model(self, job_data: Dict[str, Any]) -> Optional[JobPosting]:
        """Convert raw Indeed job data to JobPosting model"""
        try:
            # Handle Indeed's URL structure
            job_url = job_data.get('url', '')
            if job_url:
                if not job_url.startswith('http'):
                    job_url = urljoin(self.base_url, job_url)
                
                # Indeed URLs often have tracking parameters, clean them
                if '?' in job_url:
                    base_url = job_url.split('?')[0]
                    job_url = base_url
            
            # Combine description and salary info
            description_parts = []
            if job_data.get('description'):
                description_parts.append(job_data['description'])
            if job_data.get('salary'):
                description_parts.append(f"Salary: {job_data['salary']}")
            
            full_description = ' | '.join(description_parts) if description_parts else ''
            
            job_posting = JobPosting(
                job_url=job_url,
                title=self._clean_text(job_data.get('title', '')),
                company_name=self._clean_text(job_data.get('company_name', '')),
                location_text=self._clean_text(job_data.get('location', 'Remote')),
                source_platform=self.site_name,
                full_description_raw=self._clean_text(full_description),
                processing_status="pending"
            )
            
            return job_posting
            
        except Exception as e:
            logger.error(f"Error parsing Indeed job to model: {e}")
            return None
    
    async def _fallback_to_mock_data(self, keywords: str, num_results: int, start_time: float) -> ScraperResult:
        """Generate mock Indeed data as fallback"""
        execution_time = time.time() - start_time
        mock_jobs = self._generate_mock_jobs(keywords, num_results)
        
        return ScraperResult(
            jobs=mock_jobs,
            source=f"{self.site_name}_Mock",
            success=True,
            error_message="Used mock data due to Indeed scraping challenges",
            jobs_found=len(mock_jobs),
            execution_time=execution_time
        ) 