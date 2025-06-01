# Form Filler - Automated application form filling logic
"""
Phase 4.2: Application Automation Engine - Form Filler Service

Automatically fills job application forms using user profile data with Human-in-the-Loop review.
Supports common form fields across major job boards and company career pages.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import time
import json
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from app.models.user_profile_models import UserProfile
from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

class FormFillerService:
    """
    Service for automatically filling job application forms with user profile data.
    
    Features:
    - Intelligent form field detection
    - Multi-format form support (text, dropdowns, checkboxes, etc.)
    - Human-in-the-Loop review before submission
    - Error handling and fallback strategies
    - Screenshot capture for debugging
    """
    
    def __init__(self, headless: bool = False, slow_mo: int = 1000):
        """
        Initialize the form filler service.
        
        Args:
            headless: Run browser in headless mode (False for HITL visibility)
            slow_mo: Milliseconds to slow down operations for visibility
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Common form field mappings
        self.field_mappings = {
            'first_name': ['first_name', 'firstname', 'fname', 'first-name', 'given_name'],
            'last_name': ['last_name', 'lastname', 'lname', 'last-name', 'family_name', 'surname'],
            'full_name': ['full_name', 'fullname', 'name', 'full-name', 'applicant_name'],
            'email': ['email', 'email_address', 'e_mail', 'mail', 'contact_email'],
            'phone': ['phone', 'phone_number', 'telephone', 'mobile', 'cell', 'contact_phone'],
            'linkedin': ['linkedin', 'linkedin_url', 'linkedin_profile', 'linked_in'],
            'github': ['github', 'github_url', 'github_profile', 'portfolio'],
            'portfolio': ['portfolio', 'portfolio_url', 'website', 'personal_website'],
            'current_company': ['current_company', 'employer', 'company', 'current_employer'],
            'current_title': ['current_title', 'job_title', 'position', 'role', 'current_position'],
            'experience_years': ['experience', 'years_experience', 'total_experience', 'years_of_experience'],
            'salary_expectation': ['salary', 'expected_salary', 'salary_expectation', 'desired_salary'],
            'location': ['location', 'city', 'address', 'current_location', 'residence'],
            'availability': ['availability', 'start_date', 'available_date', 'notice_period'],
            'cover_letter': ['cover_letter', 'motivation', 'why_interested', 'message']
        }
        
        logger.info("FormFillerService initialized")
    
    async def start_browser(self) -> None:
        """Initialize browser and context."""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            self.page = await self.context.new_page()
            logger.info("Browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def close_browser(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    async def navigate_to_application(self, job_url: str) -> bool:
        """
        Navigate to job application page.
        
        Args:
            job_url: URL of the job posting or application page
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            if not self.page:
                await self.start_browser()
            
            logger.info(f"Navigating to: {job_url}")
            await self.page.goto(job_url, wait_until='networkidle')
            
            # Wait for page to load
            await self.page.wait_for_timeout(2000)
            
            # Look for "Apply" button and click if found
            apply_selectors = [
                'a[href*="apply"]', 'button:has-text("Apply")', 
                'a:has-text("Apply")', '[data-testid*="apply"]',
                'button:has-text("Apply Now")', 'a:has-text("Apply Now")',
                '.apply-button', '#apply-button', '.btn-apply'
            ]
            
            for selector in apply_selectors:
                try:
                    apply_button = await self.page.query_selector(selector)
                    if apply_button:
                        logger.info(f"Found apply button with selector: {selector}")
                        await apply_button.click()
                        await self.page.wait_for_timeout(3000)
                        break
                except:
                    continue
            
            # Check if we're on an application form page
            form_indicators = ['form', 'input[type="text"]', 'input[type="email"]', 'textarea']
            has_form = False
            for indicator in form_indicators:
                if await self.page.query_selector(indicator):
                    has_form = True
                    break
            
            if has_form:
                logger.info("Successfully navigated to application form")
                return True
            else:
                logger.warning("No application form found on page")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to application: {e}")
            return False
    
    async def detect_form_fields(self) -> Dict[str, List[str]]:
        """
        Detect and categorize form fields on the current page.
        
        Returns:
            Dictionary mapping field types to their selectors
        """
        detected_fields = {}
        
        try:
            # Get all form inputs
            inputs = await self.page.query_selector_all('input, textarea, select')
            
            for input_element in inputs:
                # Get element attributes
                input_type = await input_element.get_attribute('type') or 'text'
                name = await input_element.get_attribute('name') or ''
                id_attr = await input_element.get_attribute('id') or ''
                placeholder = await input_element.get_attribute('placeholder') or ''
                label_text = ''
                
                # Try to find associated label
                try:
                    if id_attr:
                        label = await self.page.query_selector(f'label[for="{id_attr}"]')
                        if label:
                            label_text = await label.inner_text()
                except:
                    pass
                
                # Combine all text for analysis
                field_text = f"{name} {id_attr} {placeholder} {label_text}".lower()
                
                # Categorize field
                field_category = self._categorize_field(field_text, input_type)
                
                if field_category:
                    if field_category not in detected_fields:
                        detected_fields[field_category] = []
                    
                    # Create selector for this field
                    if id_attr:
                        selector = f'#{id_attr}'
                    elif name:
                        selector = f'[name="{name}"]'
                    else:
                        selector = f'input[type="{input_type}"]'
                    
                    detected_fields[field_category].append(selector)
            
            logger.info(f"Detected form fields: {list(detected_fields.keys())}")
            return detected_fields
            
        except Exception as e:
            logger.error(f"Error detecting form fields: {e}")
            return {}
    
    def _categorize_field(self, field_text: str, input_type: str) -> Optional[str]:
        """Categorize a form field based on its text content and type."""
        for category, keywords in self.field_mappings.items():
            for keyword in keywords:
                if keyword in field_text:
                    return category
        
        # Special handling for email fields
        if input_type == 'email' or 'email' in field_text:
            return 'email'
        
        # Special handling for phone fields
        if input_type == 'tel' or any(word in field_text for word in ['phone', 'tel', 'mobile']):
            return 'phone'
        
        return None
    
    async def fill_form_fields(self, user_profile: UserProfile, detected_fields: Dict[str, List[str]]) -> Dict[str, bool]:
        """
        Fill form fields with user profile data.
        
        Args:
            user_profile: User profile containing data to fill
            detected_fields: Dictionary of detected form fields
            
        Returns:
            Dictionary mapping field types to success status
        """
        fill_results = {}
        
        # Prepare data from user profile
        profile_data = self._extract_profile_data(user_profile)
        
        for field_type, selectors in detected_fields.items():
            if field_type not in profile_data:
                continue
            
            value = profile_data[field_type]
            if not value:
                continue
            
            # Try each selector for this field type
            filled = False
            for selector in selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if not element:
                        continue
                    
                    # Get element type
                    tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                    input_type = await element.get_attribute('type') or 'text'
                    
                    if tag_name == 'select':
                        # Handle dropdown
                        await self._fill_select_field(element, value)
                    elif input_type in ['checkbox', 'radio']:
                        # Handle checkbox/radio
                        await self._fill_choice_field(element, value)
                    else:
                        # Handle text input
                        await element.clear()
                        await element.fill(str(value))
                    
                    filled = True
                    logger.info(f"Filled {field_type} field with selector: {selector}")
                    break
                    
                except Exception as e:
                    logger.warning(f"Failed to fill {field_type} with selector {selector}: {e}")
                    continue
            
            fill_results[field_type] = filled
            
            # Small delay between fields
            await self.page.wait_for_timeout(500)
        
        return fill_results
    
    async def _fill_select_field(self, element, value: str) -> None:
        """Fill a select dropdown field."""
        try:
            # Try to select by visible text first
            await element.select_option(label=value)
        except:
            try:
                # Try to select by value
                await element.select_option(value=value)
            except:
                # Try partial text match
                options = await element.query_selector_all('option')
                for option in options:
                    option_text = await option.inner_text()
                    if value.lower() in option_text.lower():
                        option_value = await option.get_attribute('value')
                        await element.select_option(value=option_value)
                        break
    
    async def _fill_choice_field(self, element, value: str) -> None:
        """Fill checkbox or radio button field."""
        try:
            # For checkboxes, check if value indicates true/checked
            if value.lower() in ['yes', 'true', '1', 'checked']:
                await element.check()
            else:
                await element.uncheck()
        except:
            # For radio buttons, try to click if value matches
            await element.click()
    
    def _extract_profile_data(self, user_profile: UserProfile) -> Dict[str, Any]:
        """Extract relevant data from user profile for form filling."""
        # Split full name if available
        first_name = last_name = ""
        if user_profile.full_name:
            name_parts = user_profile.full_name.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Get current experience
        current_company = current_title = ""
        experience_years = 0
        if user_profile.experiences:
            # Find current job (no end_date or end_date is "Present")
            current_job = None
            for exp in user_profile.experiences:
                if not exp.end_date or exp.end_date.lower() in ['present', 'current']:
                    current_job = exp
                    break
            
            if current_job:
                current_company = current_job.company_name
                current_title = current_job.job_title
            
            # Calculate total experience
            for exp in user_profile.experiences:
                if hasattr(exp, 'years_of_experience'):
                    experience_years += exp.years_of_experience or 0
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'full_name': user_profile.full_name or "",
            'email': str(user_profile.email) if user_profile.email else "",
            'phone': user_profile.phone or "",
            'linkedin': str(user_profile.linkedin_url) if user_profile.linkedin_url else "",
            'github': str(user_profile.github_url) if user_profile.github_url else "",
            'portfolio': str(user_profile.portfolio_url) if user_profile.portfolio_url else "",
            'current_company': current_company,
            'current_title': current_title,
            'experience_years': str(experience_years),
            'location': user_profile.preferred_locations[0] if user_profile.preferred_locations else "",
            'salary_expectation': str(user_profile.salary_expectations_min) if user_profile.salary_expectations_min else "",
            'cover_letter': user_profile.summary_statement or ""
        }
    
    async def take_screenshot(self, filename: str = None) -> str:
        """Take a screenshot of the current page."""
        if not filename:
            filename = f"application_form_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        screenshot_path = f"data/screenshots/{filename}"
        
        try:
            await self.page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return ""
    
    async def human_review_and_submit(self, user_profile: UserProfile, job: JobPosting) -> bool:
        """
        Pause for human review and manual submission (HITL).
        
        Args:
            user_profile: User profile used for filling
            job: Job posting being applied to
            
        Returns:
            True if user confirms submission, False otherwise
        """
        try:
            # Take screenshot for review
            screenshot_path = await self.take_screenshot()
            
            print("\n" + "="*80)
            print("🤖 HUMAN-IN-THE-LOOP REVIEW REQUIRED")
            print("="*80)
            print(f"📋 Job: {job.title} at {job.company_name}")
            print(f"👤 Profile: {user_profile.profile_name}")
            print(f"📧 Email: {user_profile.email}")
            print(f"📸 Screenshot: {screenshot_path}")
            print("\nThe application form has been automatically filled.")
            print("Please review the form in the browser window and:")
            print("1. ✅ Verify all fields are correctly filled")
            print("2. ✏️  Complete any missing or custom fields")
            print("3. 📎 Upload resume/documents if required")
            print("4. ✍️  Answer any custom questions")
            print("5. 🔍 Review all information for accuracy")
            print("\n⚠️  DO NOT SUBMIT YET - Wait for your confirmation below")
            print("-"*80)
            
            # Wait for user confirmation
            while True:
                user_input = input("\nReady to submit? (y/n/cancel): ").strip().lower()
                
                if user_input in ['y', 'yes']:
                    print("✅ User confirmed submission")
                    return True
                elif user_input in ['n', 'no']:
                    print("❌ User declined submission")
                    return False
                elif user_input in ['cancel', 'c']:
                    print("🚫 Application cancelled by user")
                    return False
                else:
                    print("Please enter 'y' for yes, 'n' for no, or 'cancel'")
        
        except KeyboardInterrupt:
            print("\n🚫 Application cancelled by user (Ctrl+C)")
            return False
        except Exception as e:
            logger.error(f"Error during human review: {e}")
            return False
    
    async def apply_to_job(self, job: JobPosting, user_profile: UserProfile) -> Dict[str, Any]:
        """
        Complete end-to-end job application process.
        
        Args:
            job: Job posting to apply to
            user_profile: User profile containing application data
            
        Returns:
            Dictionary with application results
        """
        result = {
            'success': False,
            'job_title': job.title,
            'company_name': job.company_name,
            'job_url': str(job.job_url),
            'filled_fields': {},
            'errors': [],
            'screenshot_path': '',
            'timestamp': datetime.utcnow()
        }
        
        try:
            logger.info(f"Starting application process for: {job.title} at {job.company_name}")
            
            # Step 1: Navigate to application page
            if not await self.navigate_to_application(str(job.job_url)):
                result['errors'].append("Failed to navigate to application page")
                return result
            
            # Step 2: Detect form fields
            detected_fields = await self.detect_form_fields()
            if not detected_fields:
                result['errors'].append("No form fields detected")
                return result
            
            # Step 3: Fill form fields
            fill_results = await self.fill_form_fields(user_profile, detected_fields)
            result['filled_fields'] = fill_results
            
            # Step 4: Take screenshot
            result['screenshot_path'] = await self.take_screenshot()
            
            # Step 5: Human review and submission
            if await self.human_review_and_submit(user_profile, job):
                result['success'] = True
                logger.info(f"Application completed successfully for {job.title}")
            else:
                result['errors'].append("User declined to submit application")
                logger.info(f"Application cancelled by user for {job.title}")
            
        except Exception as e:
            error_msg = f"Error during application process: {e}"
            result['errors'].append(error_msg)
            logger.error(error_msg, exc_info=True)
        
        return result

# Global instance for easy access
_form_filler_service = None

def get_form_filler_service(headless: bool = False) -> FormFillerService:
    """
    Get or create the global form filler service instance.
    
    Args:
        headless: Whether to run browser in headless mode
        
    Returns:
        FormFillerService instance
    """
    global _form_filler_service
    if _form_filler_service is None:
        _form_filler_service = FormFillerService(headless=headless)
    return _form_filler_service 