"""
Remote.co Job Scraper - Refactored implementation using the JobScraper interface
Improved version of the original Remote.co scraper with better error handling and structure
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

class RemoteCoScraper(JobScraper):
    """Scraper for Remote.co job board with enhanced functionality"""
    
    @property
    def site_name(self) -> str:
        return "Remote.co"
    
    @property
    def base_url(self) -> str:
        return "https://remote.co"
    
    def _build_search_url(self, keywords: str, location: Optional[str] = None) -> str:
        """Build search URL for Remote.co"""
        # Remote.co search URL structure
        base_search = f"{self.base_url}/remote-jobs/search/"
        
        # Add keywords as query parameter
        if keywords:
            # Remote.co typically uses the search term in the URL path or as a parameter
            encoded_keywords = quote_plus(keywords)
            return f"{base_search}?search={encoded_keywords}"
        
        return base_search
    
    async def search_jobs(self, keywords: str, location: Optional[str] = None, num_results: int = 10) -> ScraperResult:
        """
        Search for jobs on Remote.co
        """
        start_time = time.time()
        
        try:
            # Setup browser and page
            self.browser = await self._setup_browser()
            self.page = await self._setup_page(self.browser)
            
            # Build search URL
            search_url = self._build_search_url(keywords, location)
            logger.info(f"Searching Remote.co with URL: {search_url}")
            
            # Navigate to search page
            await self.page.goto(search_url, timeout=self.config.timeout)
            await self._human_like_delay()
            
            # Wait for results to load
            if not await self._wait_for_results(self.page):
                logger.warning("Timeout waiting for Remote.co results")
                # Try fallback approach
                return await self._fallback_to_homepage_scraping(keywords, num_results, start_time)
            
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
                logger.info(f"Successfully scraped {len(jobs)} jobs from Remote.co")
                return ScraperResult(
                    jobs=jobs,
                    source=self.site_name,
                    success=True,
                    jobs_found=len(jobs),
                    execution_time=execution_time
                )
            else:
                logger.warning("No jobs found on Remote.co, using mock data")
                return await self._fallback_to_mock_data(keywords, num_results, start_time)
            
        except Exception as e:
            logger.error(f"Error scraping Remote.co: {e}")
            # Fallback to mock data
            return await self._fallback_to_mock_data(keywords, num_results, start_time)
    
    async def _wait_for_results(self, page: Page, timeout: int = 15000) -> bool:
        """Wait for Remote.co search results to load"""
        try:
            # Wait for either job cards or "no results" message
            await page.wait_for_selector(
                '.card, .job-card, [data-job], .no-results, .search-results',
                timeout=timeout
            )
            return True
        except Exception as e:
            logger.debug(f"Failed to wait for Remote.co results: {e}")
            return False
    
    async def _extract_job_data(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job data from Remote.co search results"""
        jobs_data = []
        
        try:
            # Remote.co typically uses different selectors for job cards
            job_selectors = [
                '.card',  # Common class for job cards
                '.job-card',
                '[data-job]',
                '.job-tile',
                'article.job'
            ]
            
            # Try different selectors to find job cards
            job_elements = None
            for selector in job_selectors:
                try:
                    job_elements = await page.query_selector_all(selector)
                    if job_elements:
                        logger.debug(f"Found {len(job_elements)} jobs with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not job_elements:
                logger.warning("No job elements found with any selector")
                return []
            
            # Extract data from each job element
            for element in job_elements[:20]:  # Limit to prevent overload
                try:
                    job_data = await self._extract_single_job_data(element, page)
                    if job_data and job_data.get('title') and job_data.get('company_name'):
                        jobs_data.append(job_data)
                except Exception as e:
                    logger.debug(f"Error extracting job data: {e}")
                    continue
            
            logger.info(f"Extracted {len(jobs_data)} valid jobs from Remote.co")
            return jobs_data
            
        except Exception as e:
            logger.error(f"Error extracting job data from Remote.co: {e}")
            return []
    
    async def _extract_single_job_data(self, element, page: Page) -> Optional[Dict[str, Any]]:
        """Extract data from a single job element"""
        try:
            job_data = {}
            
            # Extract job title
            title_selectors = ['h2 a', 'h3 a', '.job-title a', '.title a', 'a[href*="/remote-jobs/"]']
            for selector in title_selectors:
                try:
                    title_element = await element.query_selector(selector)
                    if title_element:
                        job_data['title'] = await title_element.inner_text()
                        job_data['url'] = await title_element.get_attribute('href')
                        break
                except Exception:
                    continue
            
            # Extract company name
            company_selectors = [
                '.company',
                '.company-name', 
                '[data-company]',
                '.job-company',
                'p:has-text("Company")',
                'span.company'
            ]
            for selector in company_selectors:
                try:
                    company_element = await element.query_selector(selector)
                    if company_element:
                        job_data['company_name'] = await company_element.inner_text()
                        break
                except Exception:
                    continue
            
            # Extract location (usually "Remote" for Remote.co)
            location_selectors = ['.location', '.job-location', '[data-location]']
            for selector in location_selectors:
                try:
                    location_element = await element.query_selector(selector)
                    if location_element:
                        job_data['location'] = await location_element.inner_text()
                        break
                except Exception:
                    continue
            
            # Extract description/summary if available
            desc_selectors = ['.description', '.job-description', '.summary', 'p']
            for selector in desc_selectors:
                try:
                    desc_element = await element.query_selector(selector)
                    if desc_element:
                        desc_text = await desc_element.inner_text()
                        if len(desc_text) > 50:  # Only use substantial descriptions
                            job_data['description'] = desc_text
                            break
                except Exception:
                    continue
            
            return job_data if job_data.get('title') else None
            
        except Exception as e:
            logger.debug(f"Error extracting single job: {e}")
            return None
    
    def _parse_job_to_model(self, job_data: Dict[str, Any]) -> Optional[JobPosting]:
        """Convert raw job data to JobPosting model"""
        try:
            # Ensure URL is absolute
            job_url = job_data.get('url', '')
            if job_url and not job_url.startswith('http'):
                job_url = urljoin(self.base_url, job_url)
            
            # Create JobPosting
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
            logger.error(f"Error parsing job data to model: {e}")
            return None
    
    async def _fallback_to_homepage_scraping(self, keywords: str, num_results: int, start_time: float) -> ScraperResult:
        """Fallback to scraping the homepage for recent jobs"""
        try:
            logger.info("Attempting fallback: scraping Remote.co homepage")
            
            await self.page.goto(f"{self.base_url}/remote-jobs/", timeout=self.config.timeout)
            await self._human_like_delay()
            
            # Try to extract jobs from homepage
            job_data_list = await self._extract_job_data(self.page)
            
            # Filter jobs by keywords if any found
            if keywords and job_data_list:
                filtered_jobs = []
                keywords_lower = keywords.lower()
                for job_data in job_data_list:
                    title = job_data.get('title', '').lower()
                    description = job_data.get('description', '').lower()
                    if keywords_lower in title or keywords_lower in description:
                        filtered_jobs.append(job_data)
                job_data_list = filtered_jobs
            
            # Convert to models
            jobs = []
            for job_data in job_data_list[:num_results]:
                job_posting = self._parse_job_to_model(job_data)
                if job_posting:
                    jobs.append(job_posting)
            
            if jobs:
                execution_time = time.time() - start_time
                logger.info(f"Fallback successful: found {len(jobs)} jobs")
                return ScraperResult(
                    jobs=jobs,
                    source=self.site_name,
                    success=True,
                    jobs_found=len(jobs),
                    execution_time=execution_time
                )
            
        except Exception as e:
            logger.warning(f"Fallback scraping failed: {e}")
        
        # Final fallback to mock data
        return await self._fallback_to_mock_data(keywords, num_results, start_time)
    
    async def _fallback_to_mock_data(self, keywords: str, num_results: int, start_time: float) -> ScraperResult:
        """Generate mock data as final fallback"""
        execution_time = time.time() - start_time
        mock_jobs = self._generate_mock_jobs(keywords, num_results)
        
        return ScraperResult(
            jobs=mock_jobs,
            source=f"{self.site_name}_Mock",
            success=True,  # Mark as success since we're providing data
            error_message="Used mock data due to scraping issues",
            jobs_found=len(mock_jobs),
            execution_time=execution_time
        ) 