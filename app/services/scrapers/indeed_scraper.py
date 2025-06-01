"""
Indeed Job Scraper - Professional implementation with advanced anti-detection
"""
import asyncio
import logging
import random
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote_plus
from playwright.async_api import Page, Browser, BrowserContext

from .base_scraper import JobScraper, ScraperResult, ScraperConfig
from app.models.job_posting_models import JobPosting
from config.enhanced_settings import enhanced_settings

# Import the browser automation service
try:
    from app.services.browser_automation_service import browser_service
    BROWSER_SERVICE_AVAILABLE = True
except ImportError:
    BROWSER_SERVICE_AVAILABLE = False
    browser_service = None

logger = logging.getLogger(__name__)

class IndeedScraper(JobScraper):
    """Professional Indeed scraper with advanced anti-detection and automation"""
    
    @property
    def site_name(self) -> str:
        return "Indeed"
    
    @property
    def base_url(self) -> str:
        return "https://indeed.com"
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self.search_url = "https://indeed.com/jobs"
        self.current_task_id = None
        
        # Enhanced Indeed-specific selectors
        self.job_selectors = [
            '[data-testid="job-title"]',       # Primary job title selector
            '.jobTitle a',                     # Traditional job title link
            '[data-testid="job-title"] a',     # Job title with test ID
            '.jobTitle-color-purple',          # Purple job title
            'h2.jobTitle a',                   # H2 job title
            '[data-jk] .jobTitle',            # Job key with title
            '.result .jobTitle',              # Result item job title
            '.slider_container .jobTitle',     # Slider job title
            'a[data-jk]',                     # Job key links
            '.jobsearch-SerpJobCard .jobTitle' # SERP job card title
        ]
        
        # Company name selectors
        self.company_selectors = [
            '[data-testid="company-name"]',    # Primary company name
            '.companyName',                    # Traditional company name
            'span.companyName',                # Span company name
            '[data-testid="company-name"] a',  # Company name link
            '.result .companyName',            # Result company name
            '.companyInfo .companyName',       # Company info section
            'a[data-testid="company-name"]'    # Company name as link
        ]
        
        # Location selectors
        self.location_selectors = [
            '[data-testid="job-location"]',    # Primary location
            '.companyLocation',                # Traditional location
            '.locationsContainer',             # Location container
            '[data-testid="job-location"] div', # Location div
            '.result .companyLocation',        # Result location
            '.companyInfo .companyLocation'    # Company info location
        ]
        
        # Salary selectors
        self.salary_selectors = [
            '[data-testid="attribute_snippet_testid"]', # Salary attribute
            '.salary-snippet',                 # Salary snippet
            '.salaryText',                    # Salary text
            '.estimated-salary',              # Estimated salary
            '[data-testid="salary-snippet"]'  # Salary test ID
        ]
    
    def _build_search_url(self, keywords: str, location: Optional[str] = None) -> str:
        """Build search URL for Indeed"""
        params = {
            'q': keywords,
            'l': location or '',
            'sort': 'date',  # Sort by most recent
            'radius': '25',  # 25 mile radius
            'limit': '50'    # Maximum results per page
        }
        
        param_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items() if v])
        return f"{self.search_url}?{param_string}"
    
    async def _update_progress(self, message: str, progress: float):
        """Update task progress if browser service is available"""
        if BROWSER_SERVICE_AVAILABLE and browser_service and self.current_task_id:
            await browser_service.update_task_progress(self.current_task_id, message, progress)
        logger.info(f"📊 Indeed: {message} ({progress}%)")
    
    async def _extract_job_data(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job data from Indeed search results page"""
        jobs_data = []
        
        try:
            await self._update_progress("Waiting for Indeed page to load completely", 35)
            
            # Wait for dynamic content and handle potential loading states
            await page.wait_for_timeout(3000)
            
            # Handle potential bot detection
            try:
                captcha_present = await page.is_visible('iframe[title*="reCAPTCHA"]', timeout=2000)
                if captcha_present:
                    logger.warning("🤖 Indeed CAPTCHA detected - may need manual intervention")
                    await self._update_progress("CAPTCHA detected - continuing with available data", 40)
            except:
                pass  # No CAPTCHA, continue normally
            
            await self._update_progress("Analyzing Indeed page structure", 45)
            
            # Try to find job cards using multiple strategies
            job_cards_found = False
            
            for selector_type, selectors in [
                ("job_titles", self.job_selectors),
                ("job_cards", ['.jobsearch-SerpJobCard', '.result', '.job_seen_beacon', '[data-jk]']),
                ("slider_items", ['.slider_container .slider_item', '.jobsearch-NoResult'])
            ]:
                
                if job_cards_found:
                    break
                    
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            logger.info(f"✅ Indeed: Found {len(elements)} elements with {selector_type} selector: {selector}")
                            
                            await self._update_progress(f"Extracting data from {len(elements)} Indeed job listings", 50)
                            
                            # Extract data based on selector type
                            if selector_type == "job_titles":
                                jobs_data = await self._extract_from_title_elements(page, elements)
                            else:
                                jobs_data = await self._extract_from_card_elements(page, elements)
                            
                            if jobs_data:
                                job_cards_found = True
                                break
                                
                    except Exception as e:
                        logger.debug(f"Indeed selector {selector} failed: {e}")
                        continue
            
            # Fallback: Extract from any job-related links
            if not jobs_data:
                logger.info("🔄 Indeed: Using fallback extraction methods")
                await self._update_progress("Using Indeed fallback extraction", 60)
                
                # Try to find any job links
                job_links = await page.query_selector_all('a[href*="/viewjob?jk="], a[href*="/clk?jk="]')
                
                for link in job_links[:20]:  # Limit to prevent overwhelming
                    try:
                        link_data = await link.evaluate("""
                            (el) => {
                                const title = el.textContent?.trim() || el.getAttribute('aria-label') || '';
                                const href = el.href || el.getAttribute('href') || '';
                                
                                // Find parent container for additional info
                                let parent = el.closest('.jobsearch-SerpJobCard, .result, [data-jk]');
                                let company = '';
                                let location = '';
                                
                                if (parent) {
                                    const companyEl = parent.querySelector('.companyName, [data-testid="company-name"]');
                                    company = companyEl?.textContent?.trim() || '';
                                    
                                    const locationEl = parent.querySelector('.companyLocation, [data-testid="job-location"]');
                                    location = locationEl?.textContent?.trim() || '';
                                }
                                
                                return {
                                    title: title,
                                    company: company || 'Unknown Company',
                                    location: location || 'Unknown Location',
                                    job_url: href,
                                    description: title,
                                    source: 'indeed.com'
                                };
                            }
                        """)
                        
                        if link_data.get('title') and len(link_data['title']) > 5:
                            # Fix relative URLs
                            if link_data.get('job_url') and not link_data['job_url'].startswith('http'):
                                link_data['job_url'] = urljoin(self.base_url, link_data['job_url'])
                            
                            jobs_data.append(link_data)
                            
                    except Exception as e:
                        logger.debug(f"Error extracting Indeed job link: {e}")
                        continue
            
            await self._update_progress(f"Successfully extracted {len(jobs_data)} Indeed job listings", 80)
            return jobs_data
            
        except Exception as e:
            logger.error(f"Indeed element detection failed: {e}")
            await self._update_progress(f"Indeed extraction failed: {str(e)}", 80)
            return []
    
    async def _extract_from_title_elements(self, page: Page, title_elements: List) -> List[Dict[str, Any]]:
        """Extract job data when we found title elements"""
        jobs_data = []
        
        for element in title_elements:
            try:
                job_data = await element.evaluate("""
                    (titleEl) => {
                        const title = titleEl.textContent?.trim() || titleEl.getAttribute('title') || '';
                        const href = titleEl.href || titleEl.getAttribute('href') || '';
                        
                        // Find the job card container
                        let jobCard = titleEl.closest('.jobsearch-SerpJobCard, .result, [data-jk], .slider_item');
                        
                        let company = '';
                        let location = '';
                        let salary = '';
                        let description = '';
                        
                        if (jobCard) {
                            // Extract company
                            const companySelectors = [
                                '.companyName', '[data-testid="company-name"]', 
                                '.companyInfo .companyName', 'span.companyName'
                            ];
                            for (const sel of companySelectors) {
                                const companyEl = jobCard.querySelector(sel);
                                if (companyEl) {
                                    company = companyEl.textContent?.trim() || '';
                                    break;
                                }
                            }
                            
                            // Extract location
                            const locationSelectors = [
                                '.companyLocation', '[data-testid="job-location"]',
                                '.locationsContainer', '.companyInfo .companyLocation'
                            ];
                            for (const sel of locationSelectors) {
                                const locationEl = jobCard.querySelector(sel);
                                if (locationEl) {
                                    location = locationEl.textContent?.trim() || '';
                                    break;
                                }
                            }
                            
                            // Extract salary if available
                            const salarySelectors = [
                                '.salary-snippet', '.salaryText', '.estimated-salary',
                                '[data-testid="attribute_snippet_testid"]'
                            ];
                            for (const sel of salarySelectors) {
                                const salaryEl = jobCard.querySelector(sel);
                                if (salaryEl) {
                                    salary = salaryEl.textContent?.trim() || '';
                                    break;
                                }
                            }
                            
                            // Extract description snippet
                            const descEl = jobCard.querySelector('.summary, .jobSnippet, [data-testid="job-snippet"]');
                            description = descEl?.textContent?.trim() || title;
                        }
                        
                        return {
                            title: title,
                            company: company || 'Unknown Company',
                            location: location || 'Not specified',
                            job_url: href,
                            salary: salary,
                            description: description || title,
                            source: 'indeed.com'
                        };
                    }
                """)
                
                if job_data.get('title') and len(job_data['title']) > 3:
                    # Fix relative URLs
                    if job_data.get('job_url') and not job_data['job_url'].startswith('http'):
                        job_data['job_url'] = urljoin(self.base_url, job_data['job_url'])
                    
                    jobs_data.append(job_data)
                    
            except Exception as e:
                logger.debug(f"Error extracting Indeed job from title element: {e}")
                continue
        
        return jobs_data
    
    async def _extract_from_card_elements(self, page: Page, card_elements: List) -> List[Dict[str, Any]]:
        """Extract job data when we found job card elements"""
        jobs_data = []
        
        for element in card_elements:
            try:
                job_data = await element.evaluate("""
                    (cardEl) => {
                        // Extract title
                        const titleSelectors = [
                            '.jobTitle a', '[data-testid="job-title"]', 
                            '.jobTitle-color-purple', 'h2.jobTitle a'
                        ];
                        let title = '';
                        let href = '';
                        
                        for (const sel of titleSelectors) {
                            const titleEl = cardEl.querySelector(sel);
                            if (titleEl) {
                                title = titleEl.textContent?.trim() || titleEl.getAttribute('title') || '';
                                href = titleEl.href || titleEl.getAttribute('href') || '';
                                break;
                            }
                        }
                        
                        // Extract company
                        const companySelectors = [
                            '.companyName', '[data-testid="company-name"]',
                            'span.companyName', '.companyInfo .companyName'
                        ];
                        let company = '';
                        for (const sel of companySelectors) {
                            const companyEl = cardEl.querySelector(sel);
                            if (companyEl) {
                                company = companyEl.textContent?.trim() || '';
                                break;
                            }
                        }
                        
                        // Extract location
                        const locationSelectors = [
                            '.companyLocation', '[data-testid="job-location"]',
                            '.locationsContainer'
                        ];
                        let location = '';
                        for (const sel of locationSelectors) {
                            const locationEl = cardEl.querySelector(sel);
                            if (locationEl) {
                                location = locationEl.textContent?.trim() || '';
                                break;
                            }
                        }
                        
                        // Extract salary
                        const salarySelectors = [
                            '.salary-snippet', '.salaryText', '.estimated-salary'
                        ];
                        let salary = '';
                        for (const sel of salarySelectors) {
                            const salaryEl = cardEl.querySelector(sel);
                            if (salaryEl) {
                                salary = salaryEl.textContent?.trim() || '';
                                break;
                            }
                        }
                        
                        // Extract description
                        const descEl = cardEl.querySelector('.summary, .jobSnippet, [data-testid="job-snippet"]');
                        const description = descEl?.textContent?.trim() || title;
                        
                        return {
                            title: title,
                            company: company || 'Unknown Company',
                            location: location || 'Not specified',
                            job_url: href,
                            salary: salary,
                            description: description,
                            source: 'indeed.com'
                        };
                    }
                """)
                
                if job_data.get('title') and len(job_data['title']) > 3:
                    # Fix relative URLs
                    if job_data.get('job_url') and not job_data['job_url'].startswith('http'):
                        job_data['job_url'] = urljoin(self.base_url, job_data['job_url'])
                    
                    jobs_data.append(job_data)
                    
            except Exception as e:
                logger.debug(f"Error extracting Indeed job from card element: {e}")
                continue
        
        return jobs_data
    
    def _parse_job_to_model(self, job_data: Dict[str, Any]) -> Optional[JobPosting]:
        """Convert raw job data to JobPosting model"""
        try:
            # Parse salary information
            salary_min = None
            salary_max = None
            salary_text = job_data.get('salary', '')
            
            if salary_text:
                # Simple salary parsing (can be enhanced)
                import re
                salary_numbers = re.findall(r'\$?([\d,]+)', salary_text)
                if len(salary_numbers) >= 2:
                    try:
                        salary_min = float(salary_numbers[0].replace(',', ''))
                        salary_max = float(salary_numbers[1].replace(',', ''))
                    except:
                        pass
                elif len(salary_numbers) == 1:
                    try:
                        salary_min = salary_max = float(salary_numbers[0].replace(',', ''))
                    except:
                        pass
            
            job = JobPosting(
                job_url=job_data.get('job_url', ''),
                title=job_data.get('title', 'Unknown Position'),
                company_name=job_data.get('company', 'Unknown Company'),
                location_text=job_data.get('location', 'Not specified'),
                source_platform=self.site_name,
                full_description_raw=job_data.get('description', ''),
                salary_min=salary_min,
                salary_max=salary_max,
                processing_status="pending"
            )
            return job
        except Exception as e:
            logger.debug(f"Error creating Indeed job posting: {e}")
            return None
    
    async def search_jobs(self, keywords: str, location: Optional[str] = None, num_results: int = 10) -> ScraperResult:
        """
        Search jobs on Indeed with advanced anti-detection and visual feedback
        """
        start_time = time.time()
        
        try:
            # Create task for progress tracking
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"Indeed Job Search: {keywords}",
                    [
                        "Setup browser",
                        "Navigate to Indeed",
                        "Search jobs",
                        "Extract data",
                        "Process results"
                    ]
                )
            
            await self._update_progress("Starting Indeed job search with anti-detection", 0)
            
            # Setup enhanced browser
            await self._update_progress("Setting up Indeed-optimized browser", 15)
            
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                if not browser_service.browser:
                    await browser_service.start_browser()
                self.browser = browser_service.browser
                page = browser_service.page
            else:
                self.browser = await self._setup_browser()
                page = await self._setup_page(self.browser)
            
            # Add Indeed-specific stealth measures
            await page.add_init_script("""
                // Indeed-specific anti-detection
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5, 6]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override webdriver detection
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                };
            """)
            
            try:
                # Navigate to Indeed search
                search_url = self._build_search_url(keywords, location)
                logger.info(f"🌐 Navigating to Indeed: {search_url}")
                
                await self._update_progress(f"Navigating to Indeed search page", 25)
                
                # Add random delay to seem more human
                await page.wait_for_timeout(random.randint(1000, 3000))
                
                if BROWSER_SERVICE_AVAILABLE and browser_service:
                    success = await browser_service.navigate_to(search_url, self.current_task_id)
                else:
                    response = await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                    success = response and response.status == 200
                
                if not success:
                    logger.warning("Indeed navigation had issues, but continuing")
                
                # Handle potential redirects or consent pages
                await page.wait_for_timeout(2000)
                current_url = page.url
                
                if 'consent' in current_url.lower() or 'privacy' in current_url.lower():
                    logger.info("📋 Handling Indeed consent/privacy page")
                    # Try to accept cookies/consent
                    consent_buttons = [
                        'button[id*="consent"]', 'button[id*="accept"]',
                        'button:has-text("Accept")', 'button:has-text("OK")',
                        'button:has-text("Continue")', '#onetrust-accept-btn-handler'
                    ]
                    for selector in consent_buttons:
                        try:
                            button = await page.query_selector(selector)
                            if button:
                                await button.click()
                                await page.wait_for_timeout(2000)
                                break
                        except:
                            continue
                
                # Extract job data
                await self._update_progress("Indeed page loaded, extracting job data", 30)
                jobs_data = await self._extract_job_data(page)
                
                # Parse to JobPosting models
                await self._update_progress("Converting Indeed data to structured format", 85)
                jobs = []
                for job_data in jobs_data[:num_results]:
                    job = self._parse_job_to_model(job_data)
                    if job:
                        jobs.append(job)
                
                success = len(jobs) > 0
                execution_time = time.time() - start_time
                
                if success:
                    await self._update_progress(f"✅ Successfully found {len(jobs)} Indeed jobs!", 100)
                    logger.info(f"✅ Successfully scraped {len(jobs)} jobs from Indeed")
                else:
                    logger.warning("⚠️ No jobs found on Indeed")
                    await self._update_progress("No jobs found on Indeed", 90)
                
                return ScraperResult(
                    jobs=jobs,
                    source=self.site_name,
                    success=success,
                    error_message=None if success else "No jobs found",
                    jobs_found=len(jobs),
                    execution_time=execution_time
                )
                
            finally:
                # Only close browser if we created it
                if not BROWSER_SERVICE_AVAILABLE and hasattr(self, 'browser') and self.browser:
                    await self.browser.close()
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Indeed scraping failed: {str(e)}"
            logger.error(error_msg)
            
            await self._update_progress(f"Indeed error: {str(e)}", error=str(e))
            
            return ScraperResult(
                jobs=[],
                source=self.site_name,
                success=False,
                error_message=error_msg,
                jobs_found=0,
                execution_time=execution_time
            ) 