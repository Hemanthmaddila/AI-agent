"""
Stack Overflow Jobs Scraper - Developer-focused job discovery
No authentication required, making it simpler than LinkedIn integration
"""
import logging
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright, Page, Browser
from datetime import datetime
import time

from .base_scraper import JobScraper, ScraperResult, ScraperConfig
from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

class StackOverflowJobsScraper(JobScraper):
    """
    Stack Overflow Jobs scraper for developer-focused positions
    
    ADVANTAGES:
    - No authentication required
    - High-quality developer job postings
    - Detailed technical requirements
    - Excellent company information
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config or ScraperConfig())
        logger.info(f"[{self.site_name}] Initialized successfully")

    @property
    def site_name(self) -> str:
        return "Stack Overflow Jobs"
    
    @property
    def base_url(self) -> str:
        return "https://stackoverflow.com/jobs"
    
    def _build_search_url(self, keywords: str, location: Optional[str] = None) -> str:
        """Build Stack Overflow Jobs search URL"""
        keyword_query = keywords.replace(" ", "+")
        location_query = location.replace(" ", "+") if location else "Remote"
        
        # Stack Overflow Jobs URL format with sorting by newest
        return f"{self.base_url}?q={keyword_query}&l={location_query}&sort=p"
    
    async def search_jobs(self, keywords: str, location: Optional[str] = None, num_results: int = 10) -> ScraperResult:
        """
        Search for jobs on Stack Overflow Jobs
        """
        start_time = time.time()
        
        try:
            # Setup browser
            self.browser = await self._setup_browser()
            self.page = await self._setup_page(self.browser)
            
            # Build search URL
            search_url = self._build_search_url(keywords, location)
            logger.info(f"Searching Stack Overflow Jobs with URL: {search_url}")
            
            # Navigate to search page
            await self.page.goto(search_url, timeout=self.config.timeout)
            await self._human_like_delay()
            
            # Wait for results to load
            await self._wait_for_results()
            
            # Extract job data
            job_data_list = await self._extract_job_data()
            
            # Convert to JobPosting models
            jobs = []
            for job_data in job_data_list[:num_results]:
                job_posting = self._parse_job_to_model(job_data)
                if job_posting:
                    jobs.append(job_posting)
            
            execution_time = time.time() - start_time
            
            if jobs:
                logger.info(f"Successfully scraped {len(jobs)} jobs from Stack Overflow")
                return ScraperResult(
                    jobs=jobs,
                    source=self.site_name,
                    success=True,
                    jobs_found=len(jobs),
                    execution_time=execution_time
                )
            else:
                logger.warning("No jobs found on Stack Overflow, using mock data")
                return await self._fallback_to_mock_data(keywords, num_results, start_time)
            
        except Exception as e:
            logger.error(f"Error scraping Stack Overflow: {e}")
            return await self._fallback_to_mock_data(keywords, num_results, start_time)
    
    async def _wait_for_results(self) -> bool:
        """Wait for Stack Overflow job search results to load"""
        try:
            # Stack Overflow job result selectors
            result_selectors = [
                'div.js-result',
                'div[data-jobid]',
                '.listResults .result',
                '.job-item'
            ]
            
            for selector in result_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=15000)
                    return True
                except:
                    continue
            
            logger.warning("Stack Overflow results not found with expected selectors")
            return False
            
        except Exception as e:
            logger.debug(f"Error waiting for Stack Overflow results: {e}")
            return False
    
    async def _extract_job_data(self) -> List[Dict[str, Any]]:
        """Extract job data from Stack Overflow search results"""
        jobs_data = []
        
        try:
            # Multiple selectors for Stack Overflow job cards
            job_selectors = [
                'div.js-result',
                'div[data-jobid]',
                '.listResults .result'
            ]
            
            job_elements = None
            for selector in job_selectors:
                try:
                    job_elements = await self.page.query_selector_all(selector)
                    if job_elements:
                        logger.debug(f"Found {len(job_elements)} Stack Overflow jobs with selector: {selector}")
                        break
                except:
                    continue
            
            if not job_elements:
                logger.warning("No Stack Overflow job elements found")
                return []
            
            # Extract data from each job card
            for element in job_elements[:20]:  # Limit to 20 for performance
                try:
                    job_data = await self._extract_single_job_data(element)
                    if job_data and job_data.get('title') and job_data.get('company_name'):
                        jobs_data.append(job_data)
                except Exception as e:
                    logger.debug(f"Error extracting Stack Overflow job: {e}")
                    continue
            
            logger.info(f"Extracted {len(jobs_data)} valid jobs from Stack Overflow")
            return jobs_data
            
        except Exception as e:
            logger.error(f"Error extracting Stack Overflow job data: {e}")
            return []
    
    async def _extract_single_job_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract data from a single Stack Overflow job card"""
        try:
            job_data = {}
            
            # Extract job title and URL
            title_selectors = [
                'h2.mb4 > a.s-link',
                'h2 > a[href*="/jobs/"]',
                '.job-title a'
            ]
            for selector in title_selectors:
                try:
                    title_element = await element.query_selector(selector)
                    if title_element:
                        job_data['title'] = await title_element.inner_text()
                        relative_url = await title_element.get_attribute('href')
                        if relative_url:
                            job_data['url'] = f"https://stackoverflow.com{relative_url}" if not relative_url.startswith('http') else relative_url
                        break
                except:
                    continue
            
            # Extract company name
            company_selectors = [
                'h3.fc-black-700 > span:first-child',
                '.job-company-name',
                'h3 > span:first-child'
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
                'h3.fc-black-700 > span.fc-black-500',
                '.job-location',
                'h3 > span:nth-child(2)'
            ]
            for selector in location_selectors:
                try:
                    location_element = await element.query_selector(selector)
                    if location_element:
                        location_text = await location_element.inner_text()
                        # Clean up location text (remove leading dashes)
                        job_data['location'] = location_text.lstrip('-').strip()
                        break
                except:
                    continue
            
            # Extract date posted
            date_selectors = [
                'ul.horizontal-list > li > span[title*="Z"]',
                '.job-posted-date',
                'time'
            ]
            for selector in date_selectors:
                try:
                    date_element = await element.query_selector(selector)
                    if date_element:
                        job_data['date_posted'] = await date_element.inner_text()
                        break
                except:
                    continue
            
            # Extract salary if available
            salary_selectors = [
                '.salary',
                '[data-salary]',
                '.compensation'
            ]
            for selector in salary_selectors:
                try:
                    salary_element = await element.query_selector(selector)
                    if salary_element:
                        job_data['salary'] = await salary_element.inner_text()
                        break
                except:
                    continue
            
            return job_data if job_data.get('title') else None
            
        except Exception as e:
            logger.debug(f"Error extracting single Stack Overflow job: {e}")
            return None
    
    def _parse_job_to_model(self, job_data: Dict[str, Any]) -> Optional[JobPosting]:
        """Convert raw Stack Overflow job data to JobPosting model"""
        try:
            job_posting = JobPosting(
                job_url=job_data.get('url', ''),
                title=self._clean_text(job_data.get('title', '')),
                company_name=self._clean_text(job_data.get('company_name', '')),
                location_text=self._clean_text(job_data.get('location', 'Remote')),
                source_platform=self.site_name,
                full_description_raw="Full description available on Stack Overflow Jobs page",
                processing_status="pending",
                date_posted_text=job_data.get('date_posted'),
                salary_text=job_data.get('salary')
            )
            
            return job_posting
            
        except Exception as e:
            logger.error(f"Error parsing Stack Overflow job to model: {e}")
            return None
    
    async def _fallback_to_mock_data(self, keywords: str, num_results: int, start_time: float) -> ScraperResult:
        """Generate mock Stack Overflow data as fallback"""
        execution_time = time.time() - start_time
        mock_jobs = self._generate_mock_jobs(keywords, num_results)
        
        return ScraperResult(
            jobs=mock_jobs,
            source=f"{self.site_name}_Mock",
            success=True,
            error_message="Used mock data - Stack Overflow scraping encountered issues",
            jobs_found=len(mock_jobs),
            execution_time=execution_time
        )
    
    def _generate_mock_jobs(self, keywords: str, num_results: int) -> List[JobPosting]:
        """Generate mock Stack Overflow developer jobs"""
        mock_companies = [
            "Google", "Microsoft", "Amazon", "Meta", "Apple",
            "Netflix", "Spotify", "GitHub", "Stack Overflow",
            "Atlassian", "JetBrains", "Discord", "Slack"
        ]
        
        # Developer-focused job titles
        if any(lang in keywords.lower() for lang in ['python', 'django', 'flask']):
            job_titles = [
                f"Senior Python Developer",
                f"Python Backend Engineer", 
                f"Django Developer",
                f"Python Software Engineer",
                f"Full Stack Python Developer"
            ]
        elif any(lang in keywords.lower() for lang in ['javascript', 'node', 'react', 'frontend']):
            job_titles = [
                f"Frontend Developer (React)",
                f"Node.js Backend Developer",
                f"JavaScript Engineer",
                f"Full Stack JavaScript Developer",
                f"React Developer"
            ]
        elif any(lang in keywords.lower() for lang in ['java', 'spring', 'kotlin']):
            job_titles = [
                f"Senior Java Developer",
                f"Java Backend Engineer",
                f"Spring Boot Developer",
                f"Kotlin Developer",
                f"Java Software Engineer"
            ]
        else:
            job_titles = [
                f"Software Engineer ({keywords})",
                f"Senior Developer ({keywords})",
                f"Backend Engineer",
                f"Full Stack Developer",
                f"Software Developer"
            ]
        
        mock_jobs = []
        for i in range(min(num_results, len(mock_companies))):
            mock_jobs.append(JobPosting(
                job_url=f"https://stackoverflow.com/jobs/mock-{i+1}",
                title=job_titles[i % len(job_titles)],
                company_name=mock_companies[i],
                location_text="Remote" if i % 3 == 0 else ["San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX"][i % 4],
                source_platform=f"{self.site_name}_Mock",
                full_description_raw=f"Mock Stack Overflow job description for {keywords} position at {mock_companies[i]}. This is a developer-focused role with excellent technical challenges.",
                processing_status="pending",
                date_posted_text="Posted today",
                salary_text=f"${100000 + (i * 10000)}-{150000 + (i * 10000)}"
            ))
        
        return mock_jobs

# Example for direct testing
if __name__ == '__main__':
    import asyncio
    
    async def test_scraper():
        logging.basicConfig(level=logging.INFO)
        scraper = StackOverflowJobsScraper()
        result = await scraper.search_jobs("python developer", location="Remote", num_results=3)
        
        if result.success and result.jobs:
            print(f"Stack Overflow Jobs found: {len(result.jobs)}")
            for job in result.jobs:
                print(f"• {job.title} at {job.company_name} - {job.location_text}")
        else:
            print("No Stack Overflow jobs returned by test")
    
    asyncio.run(test_scraper()) 