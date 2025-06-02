#!/usr/bin/env python3
"""
🚀 Complete LinkedIn Automation Workflow
Shows FULL VISIBLE automation: Login → Search → Apply → External Sites → Fill Forms
Combines your original working LinkedIn automation with new external application features
"""

import asyncio
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.live import Live
from urllib.parse import quote_plus

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

console = Console()

class CompleteLinkedInWorkflow:
    """Complete visible LinkedIn workflow with external application automation"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.screenshot_dir = "data/screenshots"
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        
        # Load comprehensive LinkedIn selectors from JSON
        try:
            with open('data/linkedin_selectors_2025.json', 'r') as f:
                linkedin_data = json.load(f)
            
            # Use comprehensive selectors from JSON
            self.selectors = {
                'login_email': '#username',
                'login_password': '#password', 
                'login_button': 'button[type="submit"]',
                'job_cards': ', '.join([s for s in linkedin_data['job_results_selectors']['job_card'] if s.strip()]),
                'job_title': ', '.join([s for s in linkedin_data['job_detail_selectors']['title'] if s.strip()]),
                'easy_apply_buttons': linkedin_data['easy_apply_button_selectors'],
                'external_apply_buttons': linkedin_data['external_apply_button_selectors'],
                'next_button': 'button[aria-label="Next"], button:has-text("Next")',
                'submit_button': 'button[aria-label="Submit application"], button:has-text("Submit")'
            }
            console.print("✅ Loaded comprehensive LinkedIn selectors from JSON")
        except Exception as e:
            console.print(f"⚠️ Could not load selectors JSON: {e}")
            # Fallback to basic selectors
            self.selectors = {
                'login_email': '#username',
                'login_password': '#password', 
                'login_button': 'button[type="submit"]',
                'job_cards': '.job-card-container, .jobs-search-results__list-item, [data-occludable-job-id]',
                'job_title': '.job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1',
                'easy_apply_buttons': ['button[aria-label*="Easy Apply"]', 'button:has-text("Easy Apply")'],
                'external_apply_buttons': ['button:has-text("Apply on company website")', 'a:has-text("Apply")', 'button:has-text("Apply"):not(:has-text("Easy Apply"))'],
                'next_button': 'button[aria-label="Next"], button:has-text("Next")',
                'submit_button': 'button[aria-label="Submit application"], button:has-text("Submit")'
            }
    
    async def setup_browser(self):
        """Setup visible browser with anti-detection"""
        console.print(Panel("🌐 Starting Browser with Maximum Visibility", style="cyan"))
        
        playwright = await async_playwright().start()
        
        # Launch browser with maximum visibility
        self.browser = await playwright.chromium.launch(
            headless=False,  # ALWAYS visible
            slow_mo=1000,    # Slow for visibility
            args=[
                '--start-maximized',
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security'
            ]
        )
        
        # Create context
        context = await self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        
        # Anti-detection script
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)
        
        console.print("✅ Browser launched and ready!")
        return True
    
    async def take_screenshot(self, name: str):
        """Take screenshot for documentation"""
        try:
            timestamp = datetime.now().strftime("%H-%M-%S")
            path = f"{self.screenshot_dir}/workflow_{name}_{timestamp}.png"
            await self.page.screenshot(path=path)
            console.print(f"📸 Screenshot: {name}")
        except Exception as e:
            console.print(f"❌ Screenshot failed: {e}")
    
    async def linkedin_login(self):
        """Visible LinkedIn login process"""
        console.print(Panel("🔐 LinkedIn Login Process", style="cyan"))
        
        # Navigate to LinkedIn
        console.print("🌐 Navigating to LinkedIn...")
        await self.page.goto('https://www.linkedin.com/login', timeout=30000)
        await self.take_screenshot("login_page")
        
        # Wait for page to load
        await self.page.wait_for_selector(self.selectors['login_email'], timeout=10000)
        console.print("✅ Login page loaded")
        
        # Get credentials
        console.print("\n📧 Please enter your LinkedIn credentials:")
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        
        if not email or not password:
            console.print("❌ Credentials required!")
            return False
        
        # Fill login form visibly
        console.print("⌨️ Entering email...")
        await self.page.fill(self.selectors['login_email'], email)
        await asyncio.sleep(1)
        
        console.print("⌨️ Entering password...")
        await self.page.fill(self.selectors['login_password'], password)
        await asyncio.sleep(1)
        
        console.print("🖱️ Clicking login button...")
        await self.page.click(self.selectors['login_button'])
        await self.take_screenshot("login_clicked")
        
        # Wait for login to complete
        try:
            await self.page.wait_for_url("**/feed/**", timeout=15000)
            console.print("✅ Successfully logged in!")
            await self.take_screenshot("logged_in")
            return True
        except:
            console.print("⚠️ Login may need verification - check browser")
            await asyncio.sleep(10)  # Give time for manual verification
            return True
    
    async def search_jobs(self, keywords: str = "Python Developer", location: str = "Remote"):
        """Visible job search process using direct URL navigation"""
        console.print(Panel(f"🔍 Searching for: {keywords} in {location}", style="cyan"))
        
        # Use direct URL approach like your working files
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(keywords)}&location={quote_plus(location)}&f_TPR=r86400&f_AL=true"
        
        console.print(f"🌐 Navigating directly to search URL...")
        await self.page.goto(search_url, timeout=30000)
        await self.take_screenshot("search_results")
        
        # Wait for results to load
        console.print("⏳ Waiting for job results to load...")
        await asyncio.sleep(5)  # Give time for dynamic content
        
        console.print("✅ Search completed!")
        return True
    
    async def find_and_apply_to_jobs(self, max_jobs: int = 3):
        """Find jobs and demonstrate both Easy Apply and External Apply"""
        console.print(Panel(f"🎯 Analyzing Jobs and Applying (Max: {max_jobs})", style="cyan"))
        
        applications_made = 0
        
        # Wait for job cards to load with better error handling
        try:
            console.print("⏳ Waiting for job listings to load...")
            await self.page.wait_for_selector(self.selectors['job_cards'], timeout=15000)
        except Exception as e:
            console.print(f"⚠️ No job cards found with primary selectors: {e}")
            
            # Try fallback selectors
            fallback_selectors = [
                '.jobs-search-results-list .jobs-search-results__list-item',
                '.job-card-container',
                '[data-job-id]',
                '.jobs-search__results-list li'
            ]
            
            job_cards = []
            for selector in fallback_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    job_cards = await self.page.query_selector_all(selector)
                    if job_cards:
                        console.print(f"✅ Found {len(job_cards)} jobs with fallback selector: {selector}")
                        break
                except:
                    continue
            
            if not job_cards:
                console.print("❌ No job listings found. Possible reasons:")
                console.print("   1. Search terms may be too specific or unusual")
                console.print("   2. LinkedIn may be showing different layout")
                console.print("   3. Page may not have loaded completely")
                console.print("📸 Taking screenshot for debugging...")
                await self.take_screenshot("no_jobs_found")
                return 0
        
        # Get initial job count
        job_cards = await self.page.query_selector_all(self.selectors['job_cards'])
        total_jobs = len(job_cards)
        console.print(f"📋 Found {total_jobs} job listings")
        
        # Process jobs one by one (re-query each time to avoid stale references)
        for i in range(min(total_jobs, max_jobs * 2)):  # Check more than needed
            if applications_made >= max_jobs:
                break
            
            try:
                console.print(f"\n🔍 Analyzing Job #{i+1}")
                
                # Re-query job cards to get fresh references
                current_job_cards = await self.page.query_selector_all(self.selectors['job_cards'])
                if i >= len(current_job_cards):
                    console.print(f"⚠️ Job #{i+1} no longer available - skipping")
                    continue
                
                job_card = current_job_cards[i]
                
                # Click job card to view details
                await job_card.scroll_into_view_if_needed()
                await asyncio.sleep(1)
                await job_card.click()
                await asyncio.sleep(3)  # Wait for job details to load
                await self.take_screenshot(f"job_{i+1}_details")
                
                # Try to get job title
                try:
                    title_element = await self.page.query_selector(self.selectors['job_title'])
                    if title_element:
                        title = await title_element.text_content()
                        console.print(f"📄 Job Title: {title.strip()[:50]}...")
                except:
                    console.print("📄 Job Title: Not found")
                
                # Check for Easy Apply first
                easy_apply_btn = None
                for selector in self.selectors['easy_apply_buttons']:
                    try:
                        easy_apply_btn = await self.page.query_selector(selector)
                        if easy_apply_btn:
                            console.print(f"🚀 Found Easy Apply button with selector: {selector}")
                            break
                    except:
                        continue
                
                if easy_apply_btn:
                    await self.demonstrate_easy_apply(easy_apply_btn, i+1)
                    applications_made += 1
                    continue
                
                # Check for External Apply
                external_apply_btn = None
                for selector in self.selectors['external_apply_buttons']:
                    try:
                        external_apply_btn = await self.page.query_selector(selector)
                        if external_apply_btn:
                            console.print(f"🌐 Found External Apply button with selector: {selector}")
                            break
                    except:
                        continue
                
                if external_apply_btn:
                    await self.demonstrate_external_apply(external_apply_btn, i+1)
                    applications_made += 1
                    continue
                
                console.print("⚠️ No apply buttons found - skipping")
                
            except Exception as e:
                console.print(f"❌ Error with job {i+1}: {e}")
                continue
        
        console.print(f"\n✅ Application process complete! Made {applications_made} applications")
        return applications_made
    
    async def demonstrate_easy_apply(self, apply_button, job_num: int):
        """Demonstrate Easy Apply process"""
        console.print(f"🎯 Demonstrating Easy Apply for Job #{job_num}")
        
        # Scroll button into view first
        await apply_button.scroll_into_view_if_needed()
        await asyncio.sleep(1)
        
        # Click Easy Apply
        await apply_button.click()
        await asyncio.sleep(3)
        await self.take_screenshot(f"easy_apply_{job_num}_modal")
        
        # Look for form fields and demonstrate filling
        console.print("📝 Easy Apply form opened - analyzing fields...")
        
        # Wait for modal to load
        await asyncio.sleep(2)
        
        # Check for common form fields
        form_analysis = {}
        form_fields = {
            'text_inputs': 'input[type="text"]:visible',
            'email_inputs': 'input[type="email"]:visible', 
            'phone_inputs': 'input[type="tel"]:visible',
            'textareas': 'textarea:visible',
            'selects': 'select:visible',
            'file_inputs': 'input[type="file"]:visible'
        }
        
        for field_type, selector in form_fields.items():
            try:
                fields = await self.page.query_selector_all(selector)
                if fields:
                    form_analysis[field_type] = len(fields)
                    console.print(f"📋 Found {len(fields)} {field_type.replace('_', ' ')}")
            except:
                pass
        
        # Check if it's a simple or complex application
        total_fields = sum(form_analysis.values())
        
        if total_fields == 0:
            console.print("✅ No additional fields required - this is a one-click Easy Apply!")
            
            # Look for submit/next button
            submit_selectors = [
                'button[data-easy-apply-next-button]',
                'button:has-text("Submit application")',
                'button:has-text("Submit")',
                'button[aria-label*="Submit"]',
                'button[type="submit"]'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = await self.page.query_selector(selector)
                    if submit_btn:
                        console.print(f"✅ Found submit button: {selector}")
                        console.print("⚠️ DEMO MODE - Would submit application here")
                        break
                except:
                    continue
        
        elif total_fields <= 3:
            console.print("📝 Simple form detected - would fill basic fields")
            console.print("🤖 AI would map: phone, email, basic questions")
            
        else:
            console.print("📋 Complex form detected - would use full AI processing")
            console.print("🧠 AI would analyze all fields and request HITL review")
        
        # Show next steps instead of closing
        console.print("\n🔄 Next steps in full automation:")
        console.print("   1. Fill required fields with user profile data")
        console.print("   2. Upload resume if requested") 
        console.print("   3. Answer screening questions with AI")
        console.print("   4. Submit application")
        
        # Keep modal open for 5 seconds to show the form
        console.print("⏳ Showing form for 5 seconds...")
        await asyncio.sleep(5)
        
        # Close modal (in demo mode)
        console.print("❌ Closing Easy Apply modal (demo mode)")
        try:
            close_selectors = [
                'button[aria-label="Dismiss"]',
                'button:has-text("✕")',
                'button[data-test-modal-close-btn]',
                '.artdeco-modal__dismiss'
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = await self.page.query_selector(selector)
                    if close_btn:
                        await close_btn.click()
                        console.print("✅ Modal closed")
                        break
                except:
                    continue
        except:
            await self.page.press('body', 'Escape')
            console.print("✅ Modal closed with Escape key")
        
        await asyncio.sleep(1)
    
    async def demonstrate_external_apply(self, apply_button, job_num: int):
        """Demonstrate external application process"""
        console.print(f"🌐 Demonstrating External Apply for Job #{job_num}")
        
        # Scroll button into view first
        await apply_button.scroll_into_view_if_needed()
        await asyncio.sleep(1)
        
        # Get the external URL if it's a link
        external_url = None
        try:
            external_url = await apply_button.get_attribute('href')
            if external_url:
                console.print(f"🔗 External URL detected: {external_url[:60]}...")
        except:
            pass
        
        # Click external apply button (may open new tab)
        console.print("🖱️ Clicking external apply button...")
        
        # Handle potential new tab opening
        try:
            async with self.page.expect_popup(timeout=5000) as popup_info:
                await apply_button.click()
            
            # New tab opened
            external_page = await popup_info.value
            await external_page.wait_for_load_state('domcontentloaded')
            console.print("✅ External application page opened in new tab")
            
        except:
            # No new tab - button might have redirected current page
            await apply_button.click()
            await asyncio.sleep(3)
            external_page = self.page
            console.print("✅ External application page loaded in current tab")
        
        # Give page time to load
        await asyncio.sleep(5)
        
        # Take screenshot of external site
        try:
            timestamp = datetime.now().strftime("%H-%M-%S")
            await external_page.screenshot(path=f"{self.screenshot_dir}/external_site_{job_num}_{timestamp}.png")
            console.print(f"📸 Screenshot of external site taken")
        except Exception as e:
            console.print(f"⚠️ Screenshot failed: {e}")
        
        # Analyze the external site
        try:
            title = await external_page.title()
            url = external_page.url
            console.print(f"🌐 External Site Title: {title}")
            console.print(f"🔗 Current URL: {url}")
        except:
            console.print("⚠️ Could not get page details")
        
        # Check for application forms
        await self.analyze_external_form(external_page, job_num)
        
        # Show what the full automation would do
        console.print("\n🤖 Full External Application Automation would:")
        console.print("   1. Use AI to analyze form fields and page structure")
        console.print("   2. Use computer vision for complex layouts")
        console.print("   3. Fill forms with user profile data intelligently")
        console.print("   4. Request human review for ambiguous questions")
        console.print("   5. Upload resume and cover letter as needed")
        console.print("   6. Submit application with confirmation")
        
        # Keep external page open for review
        console.print("⏳ Keeping external page open for 10 seconds for review...")
        await asyncio.sleep(10)
        
        # Close external tab if it was opened separately
        if external_page != self.page:
            await external_page.close()
            console.print("❌ Closed external tab - returning to LinkedIn")
        else:
            # Navigate back to LinkedIn if in same tab
            await self.page.go_back()
            console.print("⬅️ Navigated back to LinkedIn")
    
    async def analyze_external_form(self, external_page, job_num: int):
        """Analyze external application form"""
        console.print("🔍 Analyzing external application form...")
        
        # Check for common form fields
        form_fields = {
            'text_inputs': 'input[type="text"], input[type="email"], input[type="tel"]',
            'textareas': 'textarea',
            'selects': 'select',
            'file_inputs': 'input[type="file"]',
            'submit_buttons': 'button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Apply")'
        }
        
        for field_type, selector in form_fields.items():
            try:
                elements = await external_page.query_selector_all(selector)
                if elements:
                    console.print(f"📋 Found {len(elements)} {field_type.replace('_', ' ')}")
            except:
                pass
        
        # Check for specific application form indicators
        form_indicators = [
            'form[action*="apply"]',
            'form[action*="job"]',
            'div:has-text("Application")',
            'h1:has-text("Apply")',
            'div[class*="application"]'
        ]
        
        for indicator in form_indicators:
            try:
                element = await external_page.query_selector(indicator)
                if element:
                    console.print("✅ Application form detected!")
                    break
            except:
                pass
        
        # In a real scenario, this is where we'd use the ExternalApplicationHandler
        console.print("🤖 AI Form Analysis would happen here...")
        console.print("📝 DEMO: Would fill form fields intelligently")
        console.print("🔍 DEMO: Would use vision AI for complex layouts")
        console.print("👤 DEMO: Would request human review for ambiguous fields")
    
    async def run_complete_workflow(self, keywords: str = "Python Developer", location: str = "Remote", max_jobs: int = 2):
        """Run the complete visible workflow"""
        console.print(Panel("🚀 Starting Complete LinkedIn Automation Workflow", style="bold blue"))
        
        try:
            # Step 1: Setup browser
            await self.setup_browser()
            await asyncio.sleep(2)
            
            # Step 2: Login to LinkedIn
            success = await self.linkedin_login()
            if not success:
                console.print("❌ Login failed - stopping workflow")
                return
            await asyncio.sleep(3)
            
            # Step 3: Search for jobs
            await self.search_jobs(keywords, location)
            await asyncio.sleep(3)
            
            # Step 4: Find and apply to jobs
            applications = await self.find_and_apply_to_jobs(max_jobs)
            
            # Step 5: Summary
            console.print(Panel("✅ Complete Workflow Finished!", style="green"))
            console.print(f"📊 Applications processed: {applications}")
            console.print("🎯 Demonstrated both Easy Apply and External Applications")
            console.print("🤖 External form analysis and AI capabilities showcased")
            
            # Keep browser open for review
            console.print("\n⏳ Keeping browser open for 30 seconds for review...")
            for i in range(30, 0, -1):
                console.print(f"⏰ Browser open for {i} more seconds...")
                await asyncio.sleep(1)
            
        except Exception as e:
            console.print(f"❌ Workflow error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.browser:
                await self.browser.close()
                console.print("🔒 Browser closed")

async def main():
    """Main function to run the complete workflow"""
    console.print("🎯 LinkedIn Complete Automation Workflow")
    console.print("This will show EVERYTHING: Login → Search → Apply → External Forms")
    console.print("\n" + "="*60)
    
    # Get user preferences with better defaults
    console.print("📋 Enter search criteria (or press Enter for defaults):")
    keywords = input("Job Keywords (default: Software Engineer): ").strip() or "Software Engineer"
    location = input("Location (default: United States): ").strip() or "United States"
    max_jobs_input = input("Max jobs to process (default: 3): ").strip()
    max_jobs = int(max_jobs_input) if max_jobs_input.isdigit() else 3
    
    console.print(f"\n🚀 Starting workflow:")
    console.print(f"   Keywords: {keywords}")
    console.print(f"   Location: {location}")
    console.print(f"   Max Jobs: {max_jobs}")
    
    workflow = CompleteLinkedInWorkflow()
    await workflow.run_complete_workflow(keywords, location, max_jobs)

if __name__ == "__main__":
    asyncio.run(main()) 