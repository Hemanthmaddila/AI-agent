"""
LinkedIn Job Scraper - Professional implementation with authentication and application automation
"""
import asyncio
import json
import logging
import random
import time
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, quote_plus
from playwright.async_api import Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError
from pathlib import Path

from .base_scraper import JobScraper, ScraperResult, ScraperConfig
from app.models.job_posting_models import JobPosting
from config.enhanced_settings import enhanced_settings
from app.services.vision_service import vision_service

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
        
        # Load enhanced selectors
        self.selectors = self._load_enhanced_selectors()
        
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
    
    def _load_enhanced_selectors(self) -> Dict[str, Any]:
        """Load enhanced selectors from JSON file"""
        try:
            selectors_file = Path("data/linkedin_selectors_2025.json")
            if selectors_file.exists():
                with open(selectors_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load enhanced selectors: {e}")
        
        # Return basic selectors as fallback
        return {
            "easy_apply_button_selectors": [
                "button[aria-label*='Easy Apply']",
                "button:has-text('Easy Apply')",
                ".jobs-apply-button--easyapply"
            ],
            "external_apply_button_selectors": [
                "button:has-text('Apply on company website')",
                "button:has-text('Apply now'):not(:has-text('Easy Apply'))",
                "button.jobs-apply-button:not(.jobs-apply-button--easyapply)"
            ]
        }

    async def initiate_application_on_job_page(self, job_url: str) -> Tuple[Optional[str], Optional[Page], Optional[str]]:
        """
        Navigates to a job details page and attempts to initiate an application.
        It tries to find an "Easy Apply" button first. If not found or not preferred,
        it looks for a standard "Apply" button that leads to an external site.

        Returns:
            A tuple: (application_type, page_object, message)
            application_type: "easy_apply", "external_redirect", "external_same_page_nav", or None
            page_object: The Playwright Page object (current page for Easy Apply, new page for external)
            message: URL of the new page if external, or status message.
        """
        logger.info(f"🎯 Attempting to initiate application for job: {job_url}")
        
        # Navigate to the job page
        try:
            if BROWSER_SERVICE_AVAILABLE and browser_service and browser_service.page:
                page = browser_service.page
                await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
            else:
                logger.error("No page available for navigation")
                return None, None, "No page available"
            
            # Wait for dynamic content to load
            await page.wait_for_timeout(random.uniform(2000, 4000))
            
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout loading job page {job_url}, proceeding cautiously.")
        except Exception as e:
            logger.error(f"Error navigating to job page: {e}")
            return None, None, f"Navigation error: {str(e)}"

        # First, check for Easy Apply buttons
        easy_apply_selectors = self.selectors.get('easy_apply_button_selectors', [])
        if not isinstance(easy_apply_selectors, list):
            easy_apply_selectors = [easy_apply_selectors]

        for selector in easy_apply_selectors:
            if not selector:
                continue
            try:
                easy_apply_button = await page.query_selector(selector)
                if easy_apply_button and await easy_apply_button.is_visible(timeout=5000) and await easy_apply_button.is_enabled(timeout=5000):
                    logger.info(f"✅ Found 'Easy Apply' button for {job_url}")
                    # For this implementation, we'll prioritize external applications
                    # but you can modify this logic to handle Easy Apply if preferred
                    break
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Error checking Easy Apply selector '{selector}': {e}")

        # Look for external "Apply" buttons
        external_apply_selectors = self.selectors.get('external_apply_button_selectors', [])
        if not isinstance(external_apply_selectors, list):
            external_apply_selectors = [external_apply_selectors]

        external_apply_button = None
        clicked_selector_text = "N/A"

        for selector in external_apply_selectors:
            if not selector:
                continue
            try:
                button_element = await page.query_selector(selector)
                if button_element and await button_element.is_visible(timeout=3000) and await button_element.is_enabled(timeout=3000):
                    # Additional check: ensure it's not an Easy Apply button if selectors are ambiguous
                    button_text = await button_element.text_content() or ""
                    if "easy apply" in button_text.lower() and "apply on company website" not in button_text.lower():
                        logger.info(f"Selector '{selector}' pointed to an Easy Apply button ('{button_text}'), skipping for external.")
                        continue
                    
                    external_apply_button = button_element
                    clicked_selector_text = button_text.strip()
                    logger.info(f"✅ Found potential external apply button: '{clicked_selector_text}' using selector: {selector}")
                    break
            except PlaywrightTimeoutError:
                logger.debug(f"External apply button selector timed out: {selector}")
            except Exception as e:
                logger.error(f"Error while querying selector '{selector}': {e}")
        
        if external_apply_button:
            logger.info(f"🚀 Attempting to click external apply button: '{clicked_selector_text}'")
            try:
                # Prepare to capture a new page that might open
                async with page.context.expect_page(timeout=30000) as new_page_info:
                    await external_apply_button.click() 
                    await page.wait_for_timeout(1000)

                external_page = await new_page_info.value
                await external_page.wait_for_load_state('domcontentloaded', timeout=30000)
                await external_page.bring_to_front()
                logger.info(f"✅ Successfully opened external application page: {external_page.url}")
                return "external_redirect", external_page, external_page.url
            
            except PlaywrightTimeoutError:
                logger.warning(f"Timed out waiting for new page after clicking external apply button for {job_url}. "
                               "Checking if navigation happened in the same tab.")
                await page.wait_for_timeout(3000)
                current_url_after_click = page.url
                if not current_url_after_click.startswith("https://www.linkedin.com/") and current_url_after_click != job_url:
                    logger.info(f"✅ Current page navigated to external site: {current_url_after_click}")
                    return "external_same_page_nav", page, current_url_after_click
                logger.error(f"No new page detected and current URL did not change after clicking apply for {job_url}.")
                return None, None, "Failed to detect external navigation."
            except Exception as e:
                logger.error(f"Error clicking external apply button for {job_url}: {e}")
                return None, None, f"Exception during external apply: {str(e)}"
        else:
            logger.warning(f"⚠️ No external apply button found for {job_url} after checking all CSS selectors. Trying vision-based click...")
            try:
                vision_clicked_successfully = await self.click_apply_button_with_vision(page) # page is browser_service.page
                if vision_clicked_successfully:
                    logger.info(f"✅ Vision-based apply button click reported success for {job_url}.")
                    # After a vision click, attempt to determine the outcome.
                    # This is a simplified outcome detection.
                    await page.wait_for_timeout(random.uniform(2000, 4000)) # Give page time to react

                    current_url_after_click = page.url

                    # Check if a new tab might have opened and is active (this is hard to check reliably without more context)
                    # For now, focus on same-page navigation or if it's still on LinkedIn (might be a modal).

                    if not current_url_after_click.startswith("https://www.linkedin.com/") and current_url_after_click != job_url:
                        logger.info(f"✅ Vision click likely led to external site (current page nav): {current_url_after_click}")
                        return "external_same_page_nav", page, current_url_after_click
                    elif page.url == job_url: # Still on the same page, maybe a modal appeared
                         # Check for common Easy Apply modal selectors
                        easy_apply_modal_selectors = [
                            "div[role='dialog'][aria-labelledby*='easy-apply-modal-header']",
                            ".jobs-easy-apply-modal",
                            "div.artdeco-modal[aria-modal='true']" # A generic modal selector
                        ]
                        modal_found = False
                        for selector in easy_apply_modal_selectors:
                            if await page.query_selector(selector):
                                logger.info(f"✅ Vision click likely opened an Easy Apply modal (selector '{selector}' found).")
                                modal_found = True
                                break
                        if modal_found:
                             return "easy_apply_modal_opened", page, "Easy Apply modal likely opened by vision click"
                        else:
                            logger.info("Vision click performed, but current URL is unchanged and no obvious Easy Apply modal detected. Outcome unclear.")
                            return "vision_apply_unknown_outcome", page, "Vision click performed, outcome unclear"
                    else: # URL changed but still on LinkedIn
                        logger.info(f"Vision click led to a new LinkedIn page: {current_url_after_click}. Outcome unclear.")
                        return "vision_apply_linkedin_nav", page, f"Vision click led to LinkedIn page: {current_url_after_click}"

                else:
                    logger.error(f"❌ All attempts to click an apply button (CSS and vision) failed for {job_url}.")
                    return None, None, "No apply button found (CSS or vision)."
            except Exception as e:
                logger.error(f"Error during vision-based apply attempt or outcome determination: {e}")
                return None, None, f"Exception during vision apply: {str(e)}"

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

    async def search_jobs_with_filters(
        self,
        keywords: str,
        location: Optional[str] = None,
        num_results: int = 10,
        date_posted: Optional[str] = None,
        experience_levels: Optional[List[str]] = None,
        work_modalities: Optional[List[str]] = None,
        enable_easy_apply_filter: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Enhanced job search with intelligent filtering
        
        Args:
            keywords: Job search keywords
            location: Job location
            num_results: Number of results to return
            date_posted: "Past 24 hours", "Past week", "Past month", "Any time"
            experience_levels: List of levels like ["Entry level", "Mid-Senior level"]
            work_modalities: List of types like ["Remote", "Hybrid"]
            enable_easy_apply_filter: Whether to filter for Easy Apply jobs
            
        Returns:
            List of filtered job data
        """
        try:
            await self._update_progress("Starting intelligent LinkedIn job search", 0)
            
            # Setup browser and navigate to search
            search_url = self._build_search_url(keywords, location)
            logger.info(f"🔍 Starting filtered search: {search_url}")
            
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                if not browser_service.browser:
                    await browser_service.start_browser()
                page = browser_service.page
                await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            else:
                raise Exception("Browser service not available")
            
            await self._update_progress("Applying intelligent search filters", 20)
            
            # Apply the sophisticated filters
            filter_success = await self._apply_search_filters(
                page=page,
                date_posted=date_posted,
                experience_levels=experience_levels,
                work_modalities=work_modalities,
                enable_easy_apply_filter=enable_easy_apply_filter
            )
            
            if not filter_success:
                logger.warning("⚠️ Filter application failed, proceeding with basic search")
            
            await self._update_progress("Extracting filtered job results", 60)
            
            # Extract jobs from filtered results
            jobs_data = await self._extract_job_data(page)
            
            await self._update_progress(f"Successfully found {len(jobs_data)} filtered jobs", 100)
            
            return jobs_data[:num_results]
            
        except Exception as e:
            logger.error(f"❌ Enhanced job search failed: {e}")
            return []

    async def _apply_search_filters(
        self,
        page: Page,
        date_posted: Optional[str] = None,
        experience_levels: Optional[List[str]] = None,
        work_modalities: Optional[List[str]] = None,
        enable_easy_apply_filter: bool = False
    ) -> bool:
        """
        Apply sophisticated search filters to LinkedIn job search
        
        Returns:
            True if filters were successfully applied, False otherwise
        """
        try:
            logger.info("🎯 Applying intelligent search filters...")
            
            # Wait for page to load completely
            await page.wait_for_timeout(random.uniform(2000, 4000))
            
            # Try to find and click "All filters" button
            all_filters_selectors = self.selectors.get('search_filters', {}).get('all_filters_button', [])
            all_filters_button = None
            
            for selector in all_filters_selectors:
                try:
                    all_filters_button = await page.wait_for_selector(selector, state="visible", timeout=5000)
                    if all_filters_button:
                        logger.info(f"✅ Found 'All filters' button with selector: {selector}")
                        break
                except:
                    continue
            
            if not all_filters_button:
                logger.warning("⚠️ Could not find 'All filters' button, trying individual filters")
                return await self._apply_individual_filters(page, date_posted, experience_levels, work_modalities)
            
            # Click "All filters" to open modal
            await all_filters_button.click()
            logger.info("📋 Opening filters modal...")
            await page.wait_for_timeout(random.uniform(1500, 2500))
            
            # Apply Date Posted filter
            if date_posted:
                await self._apply_date_posted_filter(page, date_posted)
            
            # Apply Experience Level filters
            if experience_levels:
                await self._apply_experience_level_filters(page, experience_levels)
            
            # Apply Work Modality filters
            if work_modalities:
                await self._apply_work_modality_filters(page, work_modalities)
            
            # Apply Easy Apply filter
            if enable_easy_apply_filter:
                await self._apply_easy_apply_filter(page)
            
            # Click "Show results" to apply all filters
            await self._apply_filters_and_show_results(page)
            
            logger.info("✅ All filters applied successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error applying search filters: {e}")
            return False

    async def _apply_date_posted_filter(self, page: Page, date_posted: str) -> bool:
        """Apply date posted filter"""
        try:
            date_options = self.selectors.get('search_filters', {}).get('date_posted_filter', {}).get('options', {})
            option_key = date_posted.lower().replace(' ', '_').replace('-', '_')
            
            if option_key not in date_options:
                logger.warning(f"⚠️ Unknown date posted option: {date_posted}")
                return False
            
            option_selectors = date_options[option_key]
            for selector in option_selectors:
                try:
                    option_element = await page.query_selector(selector)
                    if option_element and await option_element.is_visible():
                        await option_element.click()
                        logger.info(f"✅ Applied date filter: {date_posted}")
                        await page.wait_for_timeout(random.uniform(500, 1000))
                        return True
                except:
                    continue
            
            logger.warning(f"⚠️ Could not apply date filter: {date_posted}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error applying date posted filter: {e}")
            return False

    async def _apply_experience_level_filters(self, page: Page, experience_levels: List[str]) -> bool:
        """Apply experience level filters"""
        try:
            exp_options = self.selectors.get('search_filters', {}).get('experience_level_filter', {}).get('options', {})
            success_count = 0
            
            for level in experience_levels:
                option_key = level.lower().replace(' ', '_').replace('-', '_')
                
                if option_key not in exp_options:
                    logger.warning(f"⚠️ Unknown experience level: {level}")
                    continue
                
                option_selectors = exp_options[option_key]
                for selector in option_selectors:
                    try:
                        option_element = await page.query_selector(selector)
                        if option_element and await option_element.is_visible():
                            await option_element.click()
                            logger.info(f"✅ Applied experience level filter: {level}")
                            await page.wait_for_timeout(random.uniform(300, 700))
                            success_count += 1
                            break
                    except:
                        continue
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error applying experience level filters: {e}")
            return False

    async def _apply_work_modality_filters(self, page: Page, work_modalities: List[str]) -> bool:
        """Apply work modality filters (Remote, Hybrid, On-site)"""
        try:
            work_options = self.selectors.get('search_filters', {}).get('work_type_filter', {}).get('options', {})
            success_count = 0
            
            for modality in work_modalities:
                option_key = modality.lower().replace(' ', '_').replace('-', '_')
                
                if option_key not in work_options:
                    logger.warning(f"⚠️ Unknown work modality: {modality}")
                    continue
                
                option_selectors = work_options[option_key]
                for selector in option_selectors:
                    try:
                        option_element = await page.query_selector(selector)
                        if option_element and await option_element.is_visible():
                            await option_element.click()
                            logger.info(f"✅ Applied work modality filter: {modality}")
                            await page.wait_for_timeout(random.uniform(300, 700))
                            success_count += 1
                            break
                    except:
                        continue
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error applying work modality filters: {e}")
            return False

    async def _apply_easy_apply_filter(self, page: Page) -> bool:
        """Apply Easy Apply filter"""
        try:
            easy_apply_selectors = self.selectors.get('search_filters', {}).get('easy_apply_filter', {}).get('toggle', [])
            
            for selector in easy_apply_selectors:
                try:
                    toggle_element = await page.query_selector(selector)
                    if toggle_element and await toggle_element.is_visible():
                        await toggle_element.click()
                        logger.info("✅ Applied Easy Apply filter")
                        await page.wait_for_timeout(random.uniform(500, 1000))
                        return True
                except:
                    continue
            
            logger.warning("⚠️ Could not apply Easy Apply filter")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error applying Easy Apply filter: {e}")
            return False

    async def _apply_filters_and_show_results(self, page: Page) -> bool:
        """Click 'Show results' button to apply all filters"""
        try:
            show_results_selectors = self.selectors.get('search_filters', {}).get('apply_filters_button', [])
            
            for selector in show_results_selectors:
                try:
                    show_results_button = await page.wait_for_selector(selector, state="visible", timeout=5000)
                    if show_results_button:
                        await show_results_button.click()
                        logger.info("🎯 Clicked 'Show results' - applying all filters...")
                        
                        # Wait for results to update
                        await page.wait_for_timeout(random.uniform(3000, 5000))
                        
                        # Wait for loading to complete
                        try:
                            loading_selectors = self.selectors.get('search_filters', {}).get('filter_loading_indicator', [])
                            for loading_selector in loading_selectors:
                                try:
                                    await page.wait_for_selector(loading_selector, state="detached", timeout=10000)
                                    break
                                except:
                                    continue
                        except:
                            pass
                        
                        logger.info("✅ Filters applied and results updated!")
                        return True
                except:
                    continue
            
            logger.warning("⚠️ Could not find 'Show results' button")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error clicking 'Show results': {e}")
            return False

    async def _apply_individual_filters(self, page: Page, date_posted: Optional[str], 
                                      experience_levels: Optional[List[str]], 
                                      work_modalities: Optional[List[str]]) -> bool:
        """Fallback method to apply individual filters if modal approach fails"""
        try:
            logger.info("🔄 Attempting individual filter application...")
            
            # This would be implemented if the "All filters" modal approach doesn't work
            # and we need to click individual filter buttons on the main search page
            
            # For now, return False to indicate filters couldn't be applied
            logger.warning("⚠️ Individual filter application not yet implemented")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error applying individual filters: {e}")
            return False

    async def _apply_filter_category_with_vision(
        self,
        main_filter_button_key: str,
        option_values_to_select: List[str],
        option_map: dict,
        filter_category_name: str,
        dropdown_apply_button_key: Optional[str] = None
    ):
        """
        Apply filters for a single category with vision fallbacks
        
        1. Try CSS selectors first (fast and precise)
        2. Fall back to vision-based interaction if selectors fail
        """
        if not option_values_to_select:
            self.logger.info(f"No options specified for {filter_category_name} filter.")
            return

        # First, try CSS selector approach
        try:
            await self._apply_filter_category_css(
                main_filter_button_key, option_values_to_select, 
                option_map, filter_category_name, dropdown_apply_button_key
            )
            return
        except Exception as e:
            self.logger.warning(f"CSS selector approach failed for {filter_category_name}: {e}")
            self.logger.info(f"Falling back to vision-based interaction for {filter_category_name}")
        
        # Fall back to vision-based approach
        await self._apply_filter_category_vision(
            filter_category_name, option_values_to_select
        )

    async def _apply_filter_category_css(
        self,
        main_filter_button_key: str,
        option_values_to_select: List[str],
        option_map: dict,
        filter_category_name: str,
        dropdown_apply_button_key: Optional[str] = None
    ):
        """Traditional CSS selector-based filtering"""
        
        # Get selectors from nested structure
        main_filter_selectors = self.selectors.get('search_filters', {}).get('top_level_filter_buttons', {}).get(main_filter_button_key, [])
        
        if not main_filter_selectors:
            raise Exception(f"No selectors found for {main_filter_button_key}")

        # Try each selector until one works
        main_filter_button = None
        for selector in main_filter_selectors:
            try:
                main_filter_button = await self.page.query_selector(selector)
                if main_filter_button and await main_filter_button.is_visible():
                    self.logger.info(f"Found {filter_category_name} button with selector: {selector}")
                    break
            except:
                continue
        
        if not main_filter_button:
            raise Exception(f"Main filter button for {filter_category_name} not found")
        
        # Click main filter button
        await main_filter_button.scroll_into_view_if_needed()
        await self.page.wait_for_timeout(500)
        await main_filter_button.click()
        await self.page.wait_for_timeout(random.uniform(1500, 2500))
        
        # Select options
        for value_to_select in option_values_to_select:
            option_selector_key = option_map.get(value_to_select)
            if not option_selector_key:
                self.logger.warning(f"No selector key found for option '{value_to_select}' in {filter_category_name}")
                continue
            
            # Get option selectors from nested structure  
            option_selectors = self.selectors.get('search_filters', {}).get(f'{filter_category_name.lower().replace(" ", "_").replace("-", "_")}_options', {}).get(option_selector_key, [])
            
            option_element = None
            for selector in option_selectors:
                try:
                    option_element = await self.page.query_selector(selector)
                    if option_element and await option_element.is_visible():
                        break
                except:
                    continue
            
            if option_element:
                self.logger.info(f"Selecting {filter_category_name} option: {value_to_select}")
                await option_element.click()
                await self.page.wait_for_timeout(random.uniform(500, 1000))
            else:
                self.logger.warning(f"Option '{value_to_select}' not found in {filter_category_name} dropdown")

        # Click apply/done button if specified
        if dropdown_apply_button_key:
            apply_selectors = self.selectors.get('search_filters', {}).get('dropdown_apply_buttons', {}).get(dropdown_apply_button_key, [])
            
            apply_button = None
            for selector in apply_selectors:
                try:
                    apply_button = await self.page.query_selector(selector)
                    if apply_button and await apply_button.is_visible():
                        break
                except:
                    continue
            
            if apply_button:
                self.logger.info(f"Clicking apply button for {filter_category_name}")
                await apply_button.click()
                await self.page.wait_for_timeout(1000)

        # Wait for results to update
        await self._wait_for_results_update()

    async def _apply_filter_category_vision(
        self,
        filter_category_name: str,
        option_values_to_select: List[str]
    ):
        """Vision-based filtering when CSS selectors fail"""
        
        try:
            # Initialize vision service
            if not vision_service.initialized:
                await vision_service.initialize()
            
            # Step 1: Take screenshot and find main filter button
            screenshot = await self.page.screenshot()
            
            element_info = await vision_service.analyze_image_for_element(
                screenshot,
                f"{filter_category_name} filter button",
                f"LinkedIn job search page with filter buttons at the top. Looking for a clickable button labeled '{filter_category_name}'"
            )
            
            if not element_info:
                raise Exception(f"Vision could not find {filter_category_name} button")
            
            # Click main filter button using vision coordinates
            center_x, center_y = await vision_service.get_element_center(element_info)
            if center_x and center_y:
                self.logger.info(f"🎯 Vision clicking {filter_category_name} button at ({center_x}, {center_y})")
                await self.page.mouse.click(center_x, center_y)
                await self.page.wait_for_timeout(2000)
            else:
                raise Exception(f"Could not get center coordinates for {filter_category_name} button")
            
            # Step 2: Take screenshot of dropdown and select options
            await self.page.wait_for_timeout(1000)  # Wait for dropdown to open
            dropdown_screenshot = await self.page.screenshot()
            
            for value_to_select in option_values_to_select:
                option_info = await vision_service.analyze_image_for_element(
                    dropdown_screenshot,
                    f"{value_to_select} option",
                    f"Dropdown menu for {filter_category_name} filter. Looking for option labeled '{value_to_select}'"
                )
                
                if option_info:
                    opt_center_x, opt_center_y = await vision_service.get_element_center(option_info)
                    if opt_center_x and opt_center_y:
                        self.logger.info(f"🎯 Vision selecting option '{value_to_select}' at ({opt_center_x}, {opt_center_y})")
                        await self.page.mouse.click(opt_center_x, opt_center_y)
                        await self.page.wait_for_timeout(500)
                else:
                    self.logger.warning(f"🔍 Vision could not find option '{value_to_select}' in {filter_category_name} dropdown")
            
            # Step 3: Look for and click apply/done button in dropdown
            apply_info = await vision_service.analyze_image_for_element(
                dropdown_screenshot,
                "Done button or Apply button",
                f"Within the {filter_category_name} dropdown, looking for a button to apply the selected filters"
            )
            
            if apply_info:
                apply_center_x, apply_center_y = await vision_service.get_element_center(apply_info)
                if apply_center_x and apply_center_y:
                    self.logger.info(f"🎯 Vision clicking apply button at ({apply_center_x}, {apply_center_y})")
                    await self.page.mouse.click(apply_center_x, apply_center_y)
                    await self.page.wait_for_timeout(1000)
            else:
                self.logger.info(f"No apply button found in {filter_category_name} dropdown - assuming auto-apply")
            
            # Wait for results to update
            await self._wait_for_results_update()
            
        except Exception as e:
            self.logger.error(f"Vision-based filtering failed for {filter_category_name}: {e}")
            raise

    async def click_apply_button_with_vision(self, page: Page) -> bool:
        logger.info("Attempting to click Apply button using vision...")
        try:
            if not vision_service.initialized:
                await vision_service.initialize()

            screenshot = await page.screenshot()
            element_description = "Apply button for a job posting, could be 'Apply', 'Easy Apply', or 'Apply now'"
            page_context = "LinkedIn job details page. Looking for the main call to action button to start an application."

            apply_button_info = await vision_service.analyze_image_for_element(
                screenshot,
                element_description,
                page_context
            )

            if apply_button_info and apply_button_info.get("found", False) and apply_button_info.get("confidence", 0) > 0.7:
                center_x, center_y = await vision_service.get_element_center(apply_button_info)
                if center_x and center_y:
                    logger.info(f"Vision found Apply button at ({center_x}, {center_y}) with confidence {apply_button_info['confidence']}. Clicking...")
                    await page.mouse.click(center_x, center_y)
                    await page.wait_for_timeout(random.uniform(1500, 2500)) # Wait for action to complete
                    return True
                else:
                    logger.warning("Vision found Apply button but could not get center coordinates.")
                    return False
            else:
                confidence = apply_button_info.get('confidence', 0) if apply_button_info else 0
                logger.warning(f"Vision did not find a suitable Apply button or confidence was too low ({confidence}).")
                return False

        except Exception as e:
            logger.error(f"Error clicking Apply button with vision: {e}")
            return False

    async def _wait_for_results_update(self):
        """Wait for job search results to update after applying filters"""
        
        # First try CSS selectors for loading indicators
        loading_selectors = self.selectors.get('search_filters', {}).get('results_update_indicators', [])
        
        for selector in loading_selectors:
            try:
                # Wait for loading indicator to appear
                await self.page.wait_for_selector(selector, state='visible', timeout=3000)
                # Then wait for it to disappear
                await self.page.wait_for_selector(selector, state='hidden', timeout=10000)
                self.logger.info("✅ Results updated (loading indicator method)")
                return
            except:
                continue
        
        # Fallback: wait for page state change using vision
        try:
            from app.services.vision_service import vision_service
            
            if vision_service.initialized:
                # Wait a moment for any loading to start
                await self.page.wait_for_timeout(1000)
                
                # Take screenshot and verify results have updated
                screenshot = await self.page.screenshot()
                results_updated = await vision_service.verify_page_state(
                    screenshot,
                    "Job search results are displayed and not loading"
                )
                
                if results_updated:
                    self.logger.info("✅ Results updated (vision verification)")
                else:
                    self.logger.warning("⚠️ Could not verify results update via vision")
            
        except Exception as e:
            self.logger.warning(f"Vision verification of results update failed: {e}")
        
        # Final fallback: simple timeout
        await self.page.wait_for_timeout(random.uniform(3000, 5000))
        self.logger.info("✅ Results update timeout completed")

    async def _apply_search_filters_sequential(
        self,
        date_posted: Optional[str] = None,
        experience_levels: Optional[List[str]] = None,
        work_modalities: Optional[List[str]] = None,
    ):
        """Apply search filters sequentially with vision fallbacks"""
        
        self.logger.info("🔍 Applying search filters sequentially (with vision fallbacks)...")
        
        # Wait for filter bar to be ready
        filter_bar_indicators = self.selectors.get('search_filters', {}).get('search_results_filter_bar_loaded_indicator', [])
        
        for indicator in filter_bar_indicators:
            try:
                await self.page.wait_for_selector(indicator, state="visible", timeout=10000)
                self.logger.info("Filter bar loaded and ready")
                break
            except:
                continue

        # Apply Date Posted filter
        if date_posted:
            option_map = {
                "Past 24 hours": "past_24_hours",
                "Past week": "past_week", 
                "Past month": "past_month",
                "Any time": "any_time",
            }
            await self._apply_filter_category_with_vision(
                main_filter_button_key="date_posted_button",
                option_values_to_select=[date_posted],
                option_map=option_map,
                filter_category_name="Date Posted",
                dropdown_apply_button_key="date_posted_apply"
            )

        # Apply Experience Level filter
        if experience_levels:
            option_map = {
                "Internship": "internship",
                "Entry level": "entry_level",
                "Associate": "associate", 
                "Mid-Senior level": "mid_senior_level",
                "Director": "director",
                "Executive": "executive",
            }
            await self._apply_filter_category_with_vision(
                main_filter_button_key="experience_level_button",
                option_values_to_select=experience_levels,
                option_map=option_map,
                filter_category_name="Experience Level",
                dropdown_apply_button_key="experience_level_apply"
            )

        # Apply Work Modality filter
        if work_modalities:
            option_map = {
                "On-site": "on_site",
                "Remote": "remote",
                "Hybrid": "hybrid",
            }
            await self._apply_filter_category_with_vision(
                main_filter_button_key="on_site_remote_button",
                option_values_to_select=work_modalities,
                option_map=option_map,
                filter_category_name="On-site/Remote",
                dropdown_apply_button_key="on_site_remote_apply"
            )

        self.logger.info("✅ All sequential filters applied successfully")

    async def find_jobs(
        self,
        keywords: str,
        location: str,
        results_limit: int = 10,
        date_posted: Optional[str] = None,
        experience_levels: Optional[List[str]] = None,
        work_modalities: Optional[List[str]] = None,
        enable_easy_apply_filter: bool = False,
        use_sequential_filtering: bool = True
    ) -> List[dict]:
        """
        Enhanced job search with sequential filtering and vision fallbacks
        
        Args:
            use_sequential_filtering: If True, uses methodical sequential approach
        """
        self.logger.info(f"🔍 Starting LinkedIn job search: Keywords='{keywords}', Location='{location}'")
        self.logger.info(f"📊 Filters: date_posted={date_posted}, experience_levels={experience_levels}, work_modalities={work_modalities}")
        
        # Perform initial search
        try:
            await self._perform_search(keywords, location)
        except Exception as e:
            self.logger.error(f"❌ Search failed: {e}")
            return []

        # Apply filters based on method preference
        if use_sequential_filtering:
            try:
                await self._apply_search_filters_sequential(
                    date_posted=date_posted,
                    experience_levels=experience_levels,
                    work_modalities=work_modalities
                )
            except Exception as e:
                self.logger.error(f"❌ Sequential filtering failed: {e}")
                self.logger.info("🔄 Falling back to traditional filtering...")
                try:
                    await self._apply_search_filters(
                        date_posted=date_posted,
                        experience_levels=experience_levels,
                        work_modalities=work_modalities,
                        enable_easy_apply_filter=enable_easy_apply_filter
                    )
                except Exception as e2:
                    self.logger.warning(f"⚠️ All filtering methods failed: {e2}")
        else:
            # Use traditional filtering method
            try:
                await self._apply_search_filters(
                    date_posted=date_posted,
                    experience_levels=experience_levels,
                    work_modalities=work_modalities,
                    enable_easy_apply_filter=enable_easy_apply_filter
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Traditional filtering failed: {e}")

        # Process job listings
        self.logger.info("📋 Processing job listings...")
        return await self._process_job_listings_page(results_limit, job_url_pattern=r"linkedin\.com/jobs/view/(\d+)") 