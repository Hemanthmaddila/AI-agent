"""
Web Browsing Service - AI-powered web browsing for career portal discovery and job applications
"""
import asyncio
import logging
import random
import time
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urljoin, urlparse
from playwright.async_api import Page, Browser, BrowserContext
import aiohttp
import json
from datetime import datetime

from config.enhanced_settings import enhanced_settings
from app.models.job_posting_models import JobPosting

# Import the browser automation service
try:
    from app.services.browser_automation_service import browser_service
    BROWSER_SERVICE_AVAILABLE = True
except ImportError:
    BROWSER_SERVICE_AVAILABLE = False
    browser_service = None

logger = logging.getLogger(__name__)

class WebBrowserService:
    """AI-powered web browsing for job discovery and application automation"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.current_task_id = None
        
        # Career page detection patterns
        self.career_keywords = enhanced_settings.CAREER_PAGE_KEYWORDS
        
        # Form field mappings for applications
        self.form_field_mapping = {
            'name': ['name', 'full_name', 'fullname', 'first_name', 'last_name', 'fname', 'lname'],
            'email': ['email', 'email_address', 'e_mail', 'mail'],
            'phone': ['phone', 'telephone', 'mobile', 'cell', 'phone_number'],
            'resume': ['resume', 'cv', 'curriculum', 'attachment', 'file'],
            'cover_letter': ['cover_letter', 'coverletter', 'letter', 'message'],
            'linkedin': ['linkedin', 'profile_url', 'social'],
            'github': ['github', 'portfolio', 'website', 'url'],
            'experience': ['experience', 'years', 'exp'],
            'salary': ['salary', 'compensation', 'expected_salary', 'wage'],
            'location': ['location', 'address', 'city', 'state'],
            'availability': ['availability', 'start_date', 'notice']
        }
    
    async def _update_progress(self, message: str, progress: float):
        """Update task progress if browser service is available"""
        if BROWSER_SERVICE_AVAILABLE and browser_service and self.current_task_id:
            await browser_service.update_task_progress(self.current_task_id, message, progress)
        logger.info(f"🌐 WebBrowser: {message} ({progress}%)")
    
    async def search_company_careers(self, company_name: str) -> List[str]:
        """Search for a company's career page URLs"""
        try:
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"Search Career Pages: {company_name}",
                    [
                        "Search for company",
                        "Find career pages",
                        "Validate URLs",
                        "Extract job listings"
                    ]
                )
            
            await self._update_progress(f"Searching for {company_name} career pages", 10)
            
            # Initialize browser
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                if not browser_service.browser:
                    await browser_service.start_browser()
                self.browser = browser_service.browser
                self.page = browser_service.page
            else:
                # Fallback browser setup
                from playwright.async_api import async_playwright
                playwright = await async_playwright().start()
                self.browser = await playwright.chromium.launch(headless=False)
                context = await self.browser.new_context()
                self.page = await context.new_page()
            
            career_urls = []
            
            # Strategy 1: Direct company website search
            await self._update_progress("Searching company website directly", 25)
            direct_urls = await self._search_company_direct(company_name)
            career_urls.extend(direct_urls)
            
            # Strategy 2: Google search for career pages
            await self._update_progress("Using Google search for career pages", 50)
            google_urls = await self._google_search_careers(company_name)
            career_urls.extend(google_urls)
            
            # Strategy 3: Common career page patterns
            await self._update_progress("Checking common career page patterns", 75)
            pattern_urls = await self._check_career_patterns(company_name)
            career_urls.extend(pattern_urls)
            
            # Remove duplicates and validate
            unique_urls = list(set(career_urls))
            validated_urls = await self._validate_career_urls(unique_urls)
            
            await self._update_progress(f"Found {len(validated_urls)} valid career pages", 100)
            
            return validated_urls
            
        except Exception as e:
            logger.error(f"Error searching company careers: {e}")
            return []
    
    async def _search_company_direct(self, company_name: str) -> List[str]:
        """Search company website directly for career pages"""
        career_urls = []
        
        try:
            # Try common company website patterns
            company_clean = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
            potential_domains = [
                f"https://{company_clean}.com",
                f"https://www.{company_clean}.com",
                f"https://{company_clean}.org",
                f"https://{company_clean}.io",
                f"https://{company_clean}.ai"
            ]
            
            for domain in potential_domains:
                try:
                    # Check if domain exists
                    async with aiohttp.ClientSession() as session:
                        async with session.get(domain, timeout=5) as response:
                            if response.status == 200:
                                # Found the main website, now look for career pages
                                career_urls.extend(await self._find_career_links(domain))
                                break
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error in direct company search: {e}")
        
        return career_urls
    
    async def _google_search_careers(self, company_name: str) -> List[str]:
        """Use Google search to find company career pages"""
        career_urls = []
        
        try:
            # Construct Google search query
            search_queries = [
                f"{company_name} careers jobs",
                f"{company_name} work with us",
                f"{company_name} employment opportunities",
                f"site:{company_name.lower().replace(' ', '')}.com careers"
            ]
            
            for query in search_queries:
                try:
                    google_url = f"https://google.com/search?q={query.replace(' ', '+')}"
                    await self.page.goto(google_url, timeout=10000)
                    await self.page.wait_for_timeout(2000)
                    
                    # Extract search result URLs
                    links = await self.page.query_selector_all('a[href]')
                    for link in links[:10]:  # Check first 10 results
                        try:
                            href = await link.get_attribute('href')
                            if href and any(keyword in href.lower() for keyword in self.career_keywords):
                                if 'google.com' not in href and 'youtube.com' not in href:
                                    career_urls.append(href)
                        except:
                            continue
                    
                    if career_urls:
                        break  # Found some URLs, no need to try other queries
                        
                except Exception as e:
                    logger.debug(f"Error in Google search: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error in Google careers search: {e}")
        
        return career_urls
    
    async def _check_career_patterns(self, company_name: str) -> List[str]:
        """Check common career page URL patterns"""
        career_urls = []
        
        try:
            company_clean = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
            base_domains = [f"{company_clean}.com", f"www.{company_clean}.com"]
            
            career_paths = [
                "/careers", "/jobs", "/opportunities", "/work-with-us",
                "/join-us", "/employment", "/talent", "/hiring",
                "/careers/", "/jobs/", "/about/careers", "/company/careers"
            ]
            
            for domain in base_domains:
                for path in career_paths:
                    career_url = f"https://{domain}{path}"
                    career_urls.append(career_url)
                    
        except Exception as e:
            logger.debug(f"Error checking career patterns: {e}")
        
        return career_urls
    
    async def _find_career_links(self, base_url: str) -> List[str]:
        """Find career page links on a company website"""
        career_urls = []
        
        try:
            await self.page.goto(base_url, timeout=10000)
            await self.page.wait_for_timeout(2000)
            
            # Look for career-related links
            links = await self.page.query_selector_all('a[href]')
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    
                    if href and text:
                        text_lower = text.lower()
                        href_lower = href.lower()
                        
                        # Check if link text or URL contains career keywords
                        if any(keyword in text_lower for keyword in self.career_keywords) or \
                           any(keyword in href_lower for keyword in self.career_keywords):
                            
                            # Convert relative URLs to absolute
                            if href.startswith('/'):
                                href = urljoin(base_url, href)
                            elif not href.startswith('http'):
                                href = urljoin(base_url, href)
                            
                            career_urls.append(href)
                            
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error finding career links: {e}")
        
        return career_urls
    
    async def _validate_career_urls(self, urls: List[str]) -> List[str]:
        """Validate that URLs are accessible and contain job-related content"""
        validated_urls = []
        
        for url in urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            content = await response.text()
                            # Check if page contains job-related content
                            content_lower = content.lower()
                            if any(keyword in content_lower for keyword in ['job', 'position', 'role', 'application', 'hire']):
                                validated_urls.append(url)
            except:
                continue
        
        return validated_urls
    
    async def scrape_career_portal(self, career_url: str, keywords: str = None) -> List[JobPosting]:
        """Scrape jobs from a career portal"""
        jobs = []
        
        try:
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"Scrape Career Portal: {career_url}",
                    [
                        "Navigate to portal",
                        "Find job listings",
                        "Extract job data",
                        "Process results"
                    ]
                )
            
            await self._update_progress("Navigating to career portal", 20)
            
            await self.page.goto(career_url, timeout=15000)
            await self.page.wait_for_timeout(3000)
            
            # Search for jobs if keywords provided
            if keywords:
                await self._search_jobs_on_portal(keywords)
            
            await self._update_progress("Extracting job listings", 50)
            
            # Extract job data using multiple strategies
            job_data_list = await self._extract_portal_jobs()
            
            # Convert to JobPosting models
            await self._update_progress("Processing job data", 80)
            
            for job_data in job_data_list:
                try:
                    job = JobPosting(
                        job_url=job_data.get('url', career_url),
                        title=job_data.get('title', 'Unknown Position'),
                        company_name=job_data.get('company', self._extract_company_from_url(career_url)),
                        location_text=job_data.get('location', 'Not specified'),
                        source_platform=f"Career Portal ({urlparse(career_url).netloc})",
                        full_description_raw=job_data.get('description', ''),
                        processing_status="pending"
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error creating job posting: {e}")
                    continue
            
            await self._update_progress(f"Found {len(jobs)} jobs on career portal", 100)
            
        except Exception as e:
            logger.error(f"Error scraping career portal: {e}")
        
        return jobs
    
    async def _search_jobs_on_portal(self, keywords: str):
        """Search for jobs on the career portal"""
        try:
            # Look for search fields
            search_selectors = [
                'input[placeholder*="search"]', 'input[name*="search"]',
                'input[id*="search"]', 'input[type="search"]',
                'input[placeholder*="job"]', 'input[placeholder*="position"]'
            ]
            
            for selector in search_selectors:
                try:
                    search_field = await self.page.query_selector(selector)
                    if search_field:
                        await search_field.fill(keywords)
                        
                        # Look for search button
                        search_buttons = [
                            'button[type="submit"]', 'input[type="submit"]',
                            'button:has-text("Search")', 'button:has-text("Find")',
                            '.search-button', '.btn-search'
                        ]
                        
                        for btn_selector in search_buttons:
                            try:
                                search_btn = await self.page.query_selector(btn_selector)
                                if search_btn:
                                    await search_btn.click()
                                    await self.page.wait_for_timeout(3000)
                                    return
                            except:
                                continue
                        
                        # Try pressing Enter
                        await search_field.press('Enter')
                        await self.page.wait_for_timeout(3000)
                        return
                        
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error searching on portal: {e}")
    
    async def _extract_portal_jobs(self) -> List[Dict[str, Any]]:
        """Extract job data from career portal"""
        jobs_data = []
        
        try:
            # Multiple strategies for finding job listings
            job_selectors = [
                '.job', '.position', '.role', '.opportunity',
                '.job-listing', '.job-item', '.job-card',
                '.position-item', '.career-opportunity',
                '[data-job]', '[data-position]',
                '.listing', '.opening'
            ]
            
            job_elements = []
            
            for selector in job_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        job_elements = elements
                        logger.info(f"Found {len(elements)} job elements with selector: {selector}")
                        break
                except:
                    continue
            
            # If no job elements found, try extracting from links
            if not job_elements:
                job_links = await self.page.query_selector_all('a[href]')
                for link in job_links:
                    try:
                        text = await link.inner_text()
                        href = await link.get_attribute('href')
                        
                        if text and href:
                            text_lower = text.lower()
                            if any(word in text_lower for word in ['developer', 'engineer', 'manager', 'analyst', 'specialist']):
                                jobs_data.append({
                                    'title': text.strip(),
                                    'url': href if href.startswith('http') else urljoin(self.page.url, href),
                                    'description': text.strip()
                                })
                    except:
                        continue
            else:
                # Extract data from job elements
                for element in job_elements:
                    try:
                        job_data = await element.evaluate("""
                            (el) => {
                                const title = el.querySelector('h1, h2, h3, h4, .title, .job-title')?.textContent?.trim() || 
                                             el.textContent?.trim() || '';
                                const link = el.querySelector('a[href]');
                                const url = link?.href || '';
                                const location = el.querySelector('.location, .job-location')?.textContent?.trim() || '';
                                const description = el.textContent?.trim() || '';
                                
                                return {
                                    title: title,
                                    url: url,
                                    location: location,
                                    description: description
                                };
                            }
                        """)
                        
                        if job_data.get('title') and len(job_data['title']) > 5:
                            jobs_data.append(job_data)
                            
                    except Exception as e:
                        logger.debug(f"Error extracting job element: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error extracting portal jobs: {e}")
        
        return jobs_data
    
    def _extract_company_from_url(self, url: str) -> str:
        """Extract company name from URL"""
        try:
            domain = urlparse(url).netloc
            # Remove common prefixes and suffixes
            company = domain.replace('www.', '').replace('.com', '').replace('.org', '').replace('.io', '')
            return company.title()
        except:
            return "Unknown Company"
    
    async def apply_to_career_portal_job(self, job_url: str, profile_data: Dict[str, Any]) -> bool:
        """Apply to a job on a career portal automatically"""
        try:
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"Apply to Job: {job_url}",
                    [
                        "Navigate to application",
                        "Fill application form",
                        "Submit application",
                        "Confirm submission"
                    ]
                )
            
            await self._update_progress("Navigating to job application page", 20)
            
            await self.page.goto(job_url, timeout=15000)
            await self.page.wait_for_timeout(3000)
            
            # Look for apply button
            apply_selectors = [
                'button:has-text("Apply")', 'a:has-text("Apply")',
                '.apply-button', '.btn-apply', '[data-apply]',
                'button:has-text("Submit Application")',
                'input[value*="Apply"]'
            ]
            
            apply_button = None
            for selector in apply_selectors:
                try:
                    apply_button = await self.page.query_selector(selector)
                    if apply_button:
                        break
                except:
                    continue
            
            if apply_button:
                await apply_button.click()
                await self.page.wait_for_timeout(3000)
            
            await self._update_progress("Filling application form", 50)
            
            # Fill application form
            success = await self._fill_application_form(profile_data)
            
            if success:
                await self._update_progress("Application form filled successfully", 80)
                
                # Ask for user confirmation before submitting
                print(f"\n🤖 Application form has been filled for: {job_url}")
                print("Review the form and press ENTER to submit, or Ctrl+C to cancel:")
                input()
                
                # Submit the form
                submit_success = await self._submit_application_form()
                
                if submit_success:
                    await self._update_progress("Application submitted successfully!", 100)
                    return True
                else:
                    await self._update_progress("Failed to submit application", 100)
                    return False
            else:
                await self._update_progress("Failed to fill application form", 100)
                return False
                
        except Exception as e:
            logger.error(f"Error applying to job: {e}")
            return False
    
    async def _fill_application_form(self, profile_data: Dict[str, Any]) -> bool:
        """Fill application form with profile data"""
        try:
            # Find all form fields
            form_fields = await self.page.query_selector_all('input, textarea, select')
            
            filled_count = 0
            total_count = len(form_fields)
            
            for field in form_fields:
                try:
                    field_type = await field.get_attribute('type') or 'text'
                    field_name = await field.get_attribute('name') or ''
                    field_id = await field.get_attribute('id') or ''
                    field_placeholder = await field.get_attribute('placeholder') or ''
                    
                    # Skip hidden and submit fields
                    if field_type in ['hidden', 'submit', 'button']:
                        continue
                    
                    # Determine field purpose
                    field_context = f"{field_name} {field_id} {field_placeholder}".lower()
                    
                    # Map fields to profile data
                    filled = False
                    
                    for field_purpose, keywords in self.form_field_mapping.items():
                        if any(keyword in field_context for keyword in keywords):
                            value = profile_data.get(field_purpose)
                            if value:
                                if field_type == 'file':
                                    # Handle file uploads (resume, etc.)
                                    if hasattr(profile_data, 'resume_path') and profile_data.get('resume_path'):
                                        await field.set_input_files(profile_data['resume_path'])
                                        filled = True
                                elif field_type in ['text', 'email', 'tel', 'url']:
                                    await field.fill(str(value))
                                    filled = True
                                elif field.tag_name.lower() == 'textarea':
                                    await field.fill(str(value))
                                    filled = True
                                break
                    
                    if filled:
                        filled_count += 1
                        
                except Exception as e:
                    logger.debug(f"Error filling form field: {e}")
                    continue
            
            logger.info(f"Filled {filled_count}/{total_count} form fields")
            return filled_count > 0
            
        except Exception as e:
            logger.error(f"Error filling application form: {e}")
            return False
    
    async def _submit_application_form(self) -> bool:
        """Submit the application form"""
        try:
            # Look for submit buttons
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Submit")', 'button:has-text("Apply")',
                'button:has-text("Send")', '.submit-button',
                '.btn-submit', '[data-submit]'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = await self.page.query_selector(selector)
                    if submit_btn:
                        await submit_btn.click()
                        await self.page.wait_for_timeout(3000)
                        
                        # Check for success indicators
                        success_indicators = [
                            'thank you', 'success', 'submitted', 'received',
                            'confirmation', 'applied'
                        ]
                        
                        page_content = await self.page.content()
                        page_content_lower = page_content.lower()
                        
                        if any(indicator in page_content_lower for indicator in success_indicators):
                            logger.info("Application submission confirmed")
                            return True
                        
                        break
                        
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error submitting application: {e}")
            return False
    
    async def discover_and_apply_workflow(self, company_name: str, keywords: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete workflow: discover career portals and apply to matching jobs"""
        results = {
            'company': company_name,
            'career_urls_found': [],
            'jobs_found': [],
            'applications_submitted': 0,
            'errors': []
        }
        
        try:
            # Step 1: Find career portals
            career_urls = await self.search_company_careers(company_name)
            results['career_urls_found'] = career_urls
            
            if not career_urls:
                results['errors'].append("No career portals found")
                return results
            
            # Step 2: Scrape jobs from each portal
            all_jobs = []
            for career_url in career_urls[:3]:  # Limit to first 3 portals
                try:
                    jobs = await self.scrape_career_portal(career_url, keywords)
                    all_jobs.extend(jobs)
                except Exception as e:
                    results['errors'].append(f"Error scraping {career_url}: {str(e)}")
            
            results['jobs_found'] = [{'title': job.title, 'url': job.job_url, 'company': job.company_name} for job in all_jobs]
            
            # Step 3: Apply to matching jobs
            for job in all_jobs[:5]:  # Limit to first 5 jobs
                try:
                    if await self.apply_to_career_portal_job(job.job_url, profile_data):
                        results['applications_submitted'] += 1
                except Exception as e:
                    results['errors'].append(f"Error applying to {job.title}: {str(e)}")
            
        except Exception as e:
            results['errors'].append(f"Workflow error: {str(e)}")
        
        return results
    
    async def close(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser and not BROWSER_SERVICE_AVAILABLE:
                await self.browser.close()
        except Exception as e:
            logger.error(f"Error closing web browser service: {e}")

# Global instance
web_browser_service = WebBrowserService() 