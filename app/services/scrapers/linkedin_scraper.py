"""
LinkedIn Job Scraper - Professional implementation with authentication and application automation
"""
import asyncio
import json
import logging
import random
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, quote_plus
from playwright.async_api import Page, Browser, BrowserContext
from pathlib import Path

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

class LinkedInScraper(JobScraper):
    """Professional LinkedIn scraper with authentication and application automation"""
    
    @property
    def site_name(self) -> str:
        return "LinkedIn"
    
    @property
    def base_url(self) -> str:
        return "https://linkedin.com"
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)
        self.search_url = "https://linkedin.com/jobs/search"
        self.current_task_id = None
        self.session_file = "linkedin_session.json"
        self.is_authenticated = False
        
        # LinkedIn-specific selectors
        self.job_selectors = [
            '[data-testid="job-card"]',         # Primary job card
            '.job-search-card',                 # Job search card
            '.job-result-card',                 # Job result card
            '.jobs-search-results__list-item',  # List item
            '.job-card-container',              # Container
            '[data-entity-urn*="job"]',        # Entity URN
            '.scaffold-layout__list-item',      # Scaffold layout
            '.jobs-search__results-list li',    # Results list
            '[data-job-id]',                   # Job ID attribute
            '.artdeco-card'                    # Artdeco card
        ]
        
        # Job detail selectors
        self.title_selectors = [
            '[data-testid="job-title"]',
            '.job-title',
            '.jobs-unified-top-card__job-title',
            '.job-details-jobs-unified-top-card__job-title',
            'h1.job-title',
            '.jobs-details__main-content h1'
        ]
        
        self.company_selectors = [
            '[data-testid="job-company"]',
            '.job-details-jobs-unified-top-card__company-name',
            '.jobs-unified-top-card__company-name',
            '.job-details-company-name',
            'a.ember-view span[dir="ltr"]'
        ]
        
        self.location_selectors = [
            '[data-testid="job-location"]',
            '.jobs-unified-top-card__bullet',
            '.job-details-jobs-unified-top-card__bullet',
            '.jobs-unified-top-card__subtitle-secondary-grouping',
            '.job-details-job-summary__location'
        ]
        
        # Application button selectors
        self.apply_button_selectors = [
            '[data-testid="apply-button"]',
            '.jobs-apply-button',
            '.job-details-how-you-match__apply-button',
            'button[aria-label*="Apply"]',
            'button:has-text("Apply")',
            'button:has-text("Easy Apply")'
        ]
    
    def _build_search_url(self, keywords: str, location: Optional[str] = None) -> str:
        """Build search URL for LinkedIn Jobs"""
        params = {
            'keywords': keywords,
            'location': location or 'Worldwide',
            'f_TPR': 'r86400',  # Past 24 hours
            'f_WT': '2',        # Remote jobs
            'sortBy': 'DD',     # Date posted descending
            'f_LF': 'f_AL',     # Easy Apply
            'start': '0'
        }
        
        param_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items() if v])
        return f"{self.search_url}?{param_string}"
    
    async def _update_progress(self, message: str, progress: float):
        """Update task progress if browser service is available"""
        if BROWSER_SERVICE_AVAILABLE and browser_service and self.current_task_id:
            await browser_service.update_task_progress(self.current_task_id, message, progress)
        logger.info(f"📊 LinkedIn: {message} ({progress}%)")
    
    async def _load_session(self, page: Page) -> bool:
        """Load saved LinkedIn session if available"""
        try:
            if not Path(self.session_file).exists():
                logger.info("No LinkedIn session file found")
                return False
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check session age (expire after 7 days)
            from datetime import datetime, timedelta
            session_time = datetime.fromisoformat(session_data.get('timestamp', ''))
            if datetime.now() - session_time > timedelta(days=7):
                logger.info("LinkedIn session expired")
                return False
            
            # Restore cookies
            cookies = session_data.get('cookies', [])
            if cookies:
                await page.context.add_cookies(cookies)
                logger.info(f"Restored {len(cookies)} LinkedIn cookies")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error loading LinkedIn session: {e}")
            return False
    
    async def _save_session(self, page: Page):
        """Save LinkedIn session for future use"""
        try:
            from datetime import datetime
            
            cookies = await page.context.cookies()
            session_data = {
                'cookies': cookies,
                'timestamp': datetime.now().isoformat(),
                'url': page.url,
                'user_agent': await page.evaluate('navigator.userAgent')
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"Saved LinkedIn session with {len(cookies)} cookies")
            
        except Exception as e:
            logger.warning(f"Error saving LinkedIn session: {e}")
    
    async def _authenticate_linkedin(self, page: Page) -> bool:
        """Handle LinkedIn authentication"""
        try:
            await self._update_progress("Checking LinkedIn authentication status", 20)
            
            # Try to load existing session first
            if await self._load_session(page):
                # Navigate to LinkedIn to check if session is valid
                await page.goto("https://linkedin.com/feed", timeout=15000)
                await page.wait_for_timeout(3000)
                
                # Check if we're logged in
                if await page.query_selector('[data-testid="nav-settings__dropdown-trigger"]'):
                    logger.info("✅ LinkedIn session restored successfully")
                    self.is_authenticated = True
                    return True
            
            # Need to authenticate
            await self._update_progress("LinkedIn authentication required", 25)
            logger.info("🔐 LinkedIn authentication required")
            
            # Navigate to login page
            await page.goto("https://linkedin.com/login", timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Check if login form is present
            if not await page.query_selector('#username'):
                logger.error("LinkedIn login form not found")
                return False
            
            print("\n" + "="*60)
            print("🔐 LINKEDIN AUTHENTICATION REQUIRED")
            print("="*60)
            print("Please log in to LinkedIn in the browser window that opened.")
            print("After logging in successfully, press ENTER here to continue...")
            print("="*60)
            
            # Wait for user to complete login
            input("Press ENTER after you've logged in to LinkedIn: ")
            
            # Wait a bit more for page to load
            await page.wait_for_timeout(3000)
            
            # Check authentication status
            try:
                await page.wait_for_selector('[data-testid="nav-settings__dropdown-trigger"]', timeout=10000)
                logger.info("✅ LinkedIn authentication successful")
                self.is_authenticated = True
                
                # Save session for future use
                await self._save_session(page)
                return True
                
            except:
                logger.error("❌ LinkedIn authentication failed or timed out")
                return False
                
        except Exception as e:
            logger.error(f"Error during LinkedIn authentication: {e}")
            return False
    
    async def _extract_job_data(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job data from LinkedIn search results"""
        jobs_data = []
        
        try:
            await self._update_progress("Waiting for LinkedIn job results to load", 40)
            
            # Wait for job results to load
            await page.wait_for_timeout(5000)
            
            # Handle potential LinkedIn loading states
            try:
                # Wait for jobs container
                await page.wait_for_selector('.jobs-search__results-list, .scaffold-layout__list', timeout=10000)
            except:
                logger.warning("LinkedIn jobs container not found - continuing anyway")
            
            await self._update_progress("Analyzing LinkedIn job listings", 50)
            
            # Try multiple job card selectors
            job_cards_found = False
            
            for selector in self.job_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        logger.info(f"✅ LinkedIn: Found {len(elements)} job cards with selector: {selector}")
                        
                        await self._update_progress(f"Extracting data from {len(elements)} LinkedIn jobs", 60)
                        
                        # Extract job data
                        for element in elements:
                            try:
                                job_data = await self._extract_linkedin_job_data(element, page)
                                if job_data and job_data.get('title'):
                                    jobs_data.append(job_data)
                            except Exception as e:
                                logger.debug(f"Error extracting LinkedIn job: {e}")
                                continue
                        
                        if jobs_data:
                            job_cards_found = True
                            break
                            
                except Exception as e:
                    logger.debug(f"LinkedIn selector {selector} failed: {e}")
                    continue
            
            # Fallback: extract from job links
            if not jobs_data:
                logger.info("🔄 LinkedIn: Using fallback extraction methods")
                await self._update_progress("Using LinkedIn fallback extraction", 65)
                
                job_links = await page.query_selector_all('a[href*="/jobs/view/"]')
                
                for link in job_links[:15]:  # Limit to prevent overwhelming
                    try:
                        link_data = await link.evaluate("""
                            (el) => {
                                const title = el.textContent?.trim() || el.getAttribute('aria-label') || '';
                                const href = el.href || el.getAttribute('href') || '';
                                
                                // Find parent job card
                                let parent = el.closest('.job-search-card, .job-result-card, .jobs-search-results__list-item, .artdeco-card');
                                let company = '';
                                let location = '';
                                
                                if (parent) {
                                    const companyEl = parent.querySelector('.job-search-card__subtitle, .job-result-card__subtitle');
                                    company = companyEl?.textContent?.trim() || '';
                                    
                                    const locationEl = parent.querySelector('.job-search-card__location, .job-result-card__location');
                                    location = locationEl?.textContent?.trim() || '';
                                }
                                
                                return {
                                    title: title,
                                    company: company || 'Unknown Company',
                                    location: location || 'Not specified',
                                    job_url: href,
                                    description: title,
                                    source: 'linkedin.com'
                                };
                            }
                        """)
                        
                        if link_data.get('title') and len(link_data['title']) > 5:
                            jobs_data.append(link_data)
                            
                    except Exception as e:
                        logger.debug(f"Error extracting LinkedIn job link: {e}")
                        continue
            
            await self._update_progress(f"Successfully extracted {len(jobs_data)} LinkedIn jobs", 75)
            return jobs_data
            
        except Exception as e:
            logger.error(f"LinkedIn job extraction failed: {e}")
            await self._update_progress(f"LinkedIn extraction error: {str(e)}", 75)
            return []
    
    async def _extract_linkedin_job_data(self, element, page: Page) -> Optional[Dict[str, Any]]:
        """Extract data from a single LinkedIn job card"""
        try:
            job_data = await element.evaluate("""
                (cardEl) => {
                    // Extract title
                    const titleSelectors = [
                        '.job-card-list__title', '.job-search-card__title',
                        '.job-result-card__title', 'h3 a', '.jobs-search-results__list-item h3'
                    ];
                    let title = '';
                    let href = '';
                    
                    for (const sel of titleSelectors) {
                        const titleEl = cardEl.querySelector(sel);
                        if (titleEl) {
                            title = titleEl.textContent?.trim() || titleEl.getAttribute('aria-label') || '';
                            href = titleEl.href || titleEl.getAttribute('href') || 
                                   titleEl.closest('a')?.href || '';
                            if (title) break;
                        }
                    }
                    
                    // Extract company
                    const companySelectors = [
                        '.job-card-container__company-name', '.job-search-card__subtitle',
                        '.job-result-card__subtitle', '.jobs-search-results__list-item h4'
                    ];
                    let company = '';
                    for (const sel of companySelectors) {
                        const companyEl = cardEl.querySelector(sel);
                        if (companyEl) {
                            company = companyEl.textContent?.trim() || '';
                            if (company) break;
                        }
                    }
                    
                    // Extract location
                    const locationSelectors = [
                        '.job-card-container__metadata-item', '.job-search-card__location',
                        '.job-result-card__location', '.jobs-search-results__list-item .job-search-card__location'
                    ];
                    let location = '';
                    for (const sel of locationSelectors) {
                        const locationEl = cardEl.querySelector(sel);
                        if (locationEl) {
                            const text = locationEl.textContent?.trim() || '';
                            if (text && !text.includes('ago') && !text.includes('applicant')) {
                                location = text;
                                break;
                            }
                        }
                    }
                    
                    // Extract description/snippet
                    const descEl = cardEl.querySelector('.job-search-card__snippet, .job-result-card__snippet');
                    const description = descEl?.textContent?.trim() || title;
                    
                    return {
                        title: title,
                        company: company || 'Unknown Company',
                        location: location || 'Not specified',
                        job_url: href,
                        description: description,
                        source: 'linkedin.com'
                    };
                }
            """)
            
            if job_data.get('title') and len(job_data['title']) > 3:
                # Fix relative URLs
                if job_data.get('job_url') and not job_data['job_url'].startswith('http'):
                    job_data['job_url'] = urljoin(self.base_url, job_data['job_url'])
                
                return job_data
                
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting LinkedIn job data: {e}")
            return None
    
    def _parse_job_to_model(self, job_data: Dict[str, Any]) -> Optional[JobPosting]:
        """Convert raw job data to JobPosting model"""
        try:
            job = JobPosting(
                job_url=job_data.get('job_url', ''),
                title=job_data.get('title', 'Unknown Position'),
                company_name=job_data.get('company', 'Unknown Company'),
                location_text=job_data.get('location', 'Not specified'),
                source_platform=self.site_name,
                full_description_raw=job_data.get('description', ''),
                processing_status="pending"
            )
            return job
        except Exception as e:
            logger.debug(f"Error creating LinkedIn job posting: {e}")
            return None
    
    async def apply_to_job(self, job_url: str, page: Page, profile_data: Dict[str, Any] = None) -> bool:
        """Apply to a LinkedIn job automatically"""
        try:
            await self._update_progress("Navigating to LinkedIn job application", 80)
            
            # Navigate to job page
            await page.goto(job_url, timeout=15000)
            await page.wait_for_timeout(3000)
            
            # Look for apply button
            apply_button = None
            for selector in self.apply_button_selectors:
                try:
                    apply_button = await page.query_selector(selector)
                    if apply_button:
                        break
                except:
                    continue
            
            if not apply_button:
                logger.warning("No apply button found on LinkedIn job page")
                return False
            
            # Click apply button
            await apply_button.click()
            await page.wait_for_timeout(3000)
            
            # Check if it's Easy Apply
            if await page.query_selector('[data-testid="jobs-apply-form"]'):
                logger.info("Found LinkedIn Easy Apply form")
                return await self._handle_easy_apply(page, profile_data)
            else:
                logger.info("External application detected - opening in new tab")
                return True  # External application, user will handle manually
                
        except Exception as e:
            logger.error(f"Error applying to LinkedIn job: {e}")
            return False
    
    async def _handle_easy_apply(self, page: Page, profile_data: Dict[str, Any] = None) -> bool:
        """Handle LinkedIn Easy Apply process"""
        try:
            await self._update_progress("Processing LinkedIn Easy Apply", 85)
            
            # Fill out the application form
            # This is a simplified implementation - can be enhanced
            
            # Look for form fields
            form_fields = await page.query_selector_all('input, textarea, select')
            
            for field in form_fields:
                try:
                    field_type = await field.get_attribute('type')
                    field_name = await field.get_attribute('name') or ''
                    field_id = await field.get_attribute('id') or ''
                    
                    # Basic field mapping
                    if 'phone' in field_name.lower() or 'phone' in field_id.lower():
                        if profile_data and profile_data.get('phone'):
                            await field.fill(profile_data['phone'])
                    elif 'email' in field_name.lower() or 'email' in field_id.lower():
                        if profile_data and profile_data.get('email'):
                            await field.fill(profile_data['email'])
                    
                except Exception as e:
                    logger.debug(f"Error filling LinkedIn form field: {e}")
                    continue
            
            # Look for submit/next button
            submit_selectors = [
                'button[aria-label*="Submit"], button[aria-label*="Next"]',
                'button:has-text("Submit")', 'button:has-text("Next")',
                '[data-testid="submit-btn"]'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = await page.query_selector(selector)
                    if submit_btn:
                        # For safety, we'll ask for user confirmation
                        print(f"\n🤖 Ready to submit LinkedIn application")
                        print("Press ENTER to submit, or Ctrl+C to cancel:")
                        input()
                        
                        await submit_btn.click()
                        await page.wait_for_timeout(2000)
                        
                        # Check for success
                        if await page.query_selector('[data-testid="application-success"]'):
                            logger.info("✅ LinkedIn application submitted successfully")
                            return True
                        break
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error in LinkedIn Easy Apply: {e}")
            return False
    
    async def search_jobs(self, keywords: str, location: Optional[str] = None, num_results: int = 10) -> ScraperResult:
        """
        Search jobs on LinkedIn with authentication and application automation
        """
        start_time = time.time()
        
        try:
            # Create task for progress tracking
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"LinkedIn Job Search: {keywords}",
                    [
                        "Setup browser",
                        "Authenticate with LinkedIn",
                        "Search jobs",
                        "Extract data",
                        "Process results"
                    ]
                )
            
            await self._update_progress("Starting LinkedIn job search with authentication", 0)
            
            # Setup enhanced browser
            await self._update_progress("Setting up LinkedIn-optimized browser", 10)
            
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                if not browser_service.browser:
                    await browser_service.start_browser()
                self.browser = browser_service.browser
                page = browser_service.page
            else:
                self.browser = await self._setup_browser()
                page = await self._setup_page(self.browser)
            
            # Add LinkedIn-specific stealth measures
            await page.add_init_script("""
                // LinkedIn-specific anti-detection
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Mock chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };
            """)
            
            try:
                # Authenticate with LinkedIn
                if not await self._authenticate_linkedin(page):
                    error_msg = "LinkedIn authentication failed"
                    await self._update_progress(error_msg, error=error_msg)
                    return ScraperResult(
                        jobs=[],
                        source=self.site_name,
                        success=False,
                        error_message=error_msg,
                        jobs_found=0,
                        execution_time=time.time() - start_time
                    )
                
                # Navigate to job search
                search_url = self._build_search_url(keywords, location)
                logger.info(f"🌐 Navigating to LinkedIn Jobs: {search_url}")
                
                await self._update_progress("Navigating to LinkedIn job search", 30)
                
                if BROWSER_SERVICE_AVAILABLE and browser_service:
                    success = await browser_service.navigate_to(search_url, self.current_task_id)
                else:
                    response = await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                    success = response and response.status == 200
                
                if not success:
                    logger.warning("LinkedIn navigation had issues, but continuing")
                
                # Extract job data
                await self._update_progress("LinkedIn jobs page loaded, extracting data", 35)
                jobs_data = await self._extract_job_data(page)
                
                # Parse to JobPosting models
                await self._update_progress("Converting LinkedIn data to structured format", 80)
                jobs = []
                for job_data in jobs_data[:num_results]:
                    job = self._parse_job_to_model(job_data)
                    if job:
                        jobs.append(job)
                
                success = len(jobs) > 0
                execution_time = time.time() - start_time
                
                if success:
                    await self._update_progress(f"✅ Successfully found {len(jobs)} LinkedIn jobs!", 100)
                    logger.info(f"✅ Successfully scraped {len(jobs)} jobs from LinkedIn")
                else:
                    logger.warning("⚠️ No jobs found on LinkedIn")
                    await self._update_progress("No jobs found on LinkedIn", 90)
                
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
            error_msg = f"LinkedIn scraping failed: {str(e)}"
            logger.error(error_msg)
            
            await self._update_progress(f"LinkedIn error: {str(e)}", error=str(e))
            
            return ScraperResult(
                jobs=[],
                source=self.site_name,
                success=False,
                error_message=error_msg,
                jobs_found=0,
                execution_time=execution_time
            ) 