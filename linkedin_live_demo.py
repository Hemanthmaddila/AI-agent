#!/usr/bin/env python3
"""
🚀 LinkedIn Job Application Agent - Live Automation Demo
Inspired by Suna AI - Shows real automated actions with visual progress
"""

import asyncio
import os
import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich import print as rprint

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

console = Console()

class LinkedInAutomationDemo:
    """Live LinkedIn automation demo with visual progress tracking"""
    
    def __init__(self):
        self.jobs_found = []
        self.applications_submitted = []
        self.session_file = "data/linkedin_session.json"
        self.screenshot_dir = "data/screenshots"
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        # Selectors for LinkedIn automation
        self.selectors = {
            'login_email': '#username',
            'login_password': '#password',
            'login_button': 'button[type="submit"]',
            'search_keywords': 'input[aria-label*="Search by title"]',
            'search_location': 'input[aria-label*="City"]',
            'job_cards': '[data-testid="job-card"], .job-search-card, .jobs-search-results__list-item',
            'job_title': '[data-testid="job-title"], .job-details-jobs-unified-top-card__job-title, h1',
            'company_name': '[data-testid="job-company"], .jobs-unified-top-card__company-name',
            'job_location': '[data-testid="job-location"], .jobs-unified-top-card__bullet',
            'easy_apply_button': 'button:has-text("Easy Apply"), [aria-label*="Easy Apply"]',
            'apply_button': 'button:has-text("Apply"), [aria-label*="Apply"]',
            'next_button': 'button[aria-label="Next"], button:has-text("Next")',
            'submit_button': 'button[aria-label="Submit application"], button:has-text("Submit")',
            'close_button': 'button[aria-label="Dismiss"], button:has-text("✕")'
        }
    
    async def create_progress_display(self):
        """Create a beautiful progress display"""
        layout = Layout()
        
        # Header
        header = Panel(
            Text("🚀 LinkedIn Job Application Agent - Live Demo", style="bold blue"),
            subtitle="Suna AI Inspired Automation",
            border_style="blue"
        )
        
        # Progress section
        progress_table = Table(show_header=True, header_style="bold magenta")
        progress_table.add_column("Step", style="cyan", width=30)
        progress_table.add_column("Status", style="green", width=20)
        progress_table.add_column("Details", style="white", width=50)
        
        layout.split_column(
            Layout(header, size=3),
            Layout(progress_table, name="progress")
        )
        
        return layout, progress_table
    
    def update_progress_table(self, table: Table, step: str, status: str, details: str):
        """Update progress table with new information"""
        table.add_row(step, status, details)
    
    async def take_screenshot(self, page: Page, name: str):
        """Take a screenshot for documentation"""
        try:
            timestamp = datetime.now().strftime("%H-%M-%S")
            screenshot_path = f"{self.screenshot_dir}/linkedin_{name}_{timestamp}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            console.print(f"📸 Screenshot saved: {screenshot_path}")
        except Exception as e:
            console.print(f"❌ Screenshot failed: {e}")
    
    async def setup_browser(self) -> tuple[Browser, Page]:
        """Setup browser with anti-detection measures"""
        console.print(Panel("🌐 Initializing Browser with Anti-Detection Measures", style="cyan"))
        
        playwright = await async_playwright().start()
        
        # Launch browser with stealth configuration
        browser = await playwright.chromium.launch(
            headless=False,  # Show browser for demo
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-default-apps',
                '--no-first-run',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-web-security',
                '--disable-plugins',
                '--disable-images',
                '--disable-javascript-harmony-shipping',
                '--disable-client-side-phishing-detection',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-report-upload',
                '--disable-logging',
                '--disable-login-animations',
                '--disable-notifications'
            ]
        )
        
        # Create context with realistic headers
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        page = await context.new_page()
        
        # Anti-detection JavaScript
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });
        """)
        
        console.print("✅ Browser initialized with stealth configuration")
        return browser, page
    
    async def linkedin_login(self, page: Page, table: Table):
        """Handle LinkedIn login with automation"""
        self.update_progress_table(table, "🔐 LinkedIn Login", "Starting", "Navigating to login page")
        
        # Navigate to LinkedIn login
        await page.goto('https://www.linkedin.com/login', timeout=30000)
        await self.take_screenshot(page, "login_page")
        
        # Wait for login form
        await page.wait_for_selector(self.selectors['login_email'], timeout=10000)
        self.update_progress_table(table, "🔐 LinkedIn Login", "Ready", "Login form loaded")
        
        # Get credentials from user
        console.print("\n" + "="*60)
        console.print("🔐 LINKEDIN AUTHENTICATION REQUIRED")
        console.print("="*60)
        console.print("Please enter your LinkedIn credentials:")
        console.print("⚠️  Your credentials are used locally and not stored")
        console.print("="*60)
        
        # For demo - you would input real credentials
        email = input("📧 LinkedIn Email: ").strip()
        password = input("🔒 LinkedIn Password: ").strip()
        
        if not email or not password:
            console.print("❌ Credentials required for automation demo")
            return False
        
        # Automated login
        self.update_progress_table(table, "🔐 LinkedIn Login", "Logging In", "Entering credentials")
        
        # Type email with human-like delays
        await page.fill(self.selectors['login_email'], email)
        await page.wait_for_timeout(random.randint(500, 1500))
        
        # Type password with human-like delays
        await page.fill(self.selectors['login_password'], password)
        await page.wait_for_timeout(random.randint(500, 1500))
        
        # Click login button
        await page.click(self.selectors['login_button'])
        await self.take_screenshot(page, "login_submitted")
        
        # Wait for login to complete with more flexible URL checking
        try:
            console.print("⏳ Waiting for login to complete...")
            
            # Wait for page change (multiple possible URLs after login)
            for i in range(30):  # Wait up to 30 seconds
                await page.wait_for_timeout(1000)
                current_url = page.url
                console.print(f"🔍 Current URL: {current_url}")
                
                # Check for successful login indicators
                if any(indicator in current_url.lower() for indicator in ['/feed', '/in/', 'linkedin.com/feed', 'linkedin.com/in']):
                    self.update_progress_table(table, "🔐 LinkedIn Login", "✅ Success", "Successfully logged into LinkedIn")
                    await self.take_screenshot(page, "login_success")
                    console.print("✅ Login successful! Proceeding with automation...")
                    return True
                
                # Check for challenges that need manual intervention
                if any(challenge in current_url.lower() for challenge in ['challenge', 'checkpoint', 'verify']):
                    self.update_progress_table(table, "🔐 LinkedIn Login", "Manual Action", "Please complete verification manually")
                    console.print("🤖 Please complete verification manually in the browser")
                    console.print("⏳ Waiting for you to complete verification...")
                    
                    # Wait for verification to complete
                    while any(challenge in page.url.lower() for challenge in ['challenge', 'checkpoint', 'verify']):
                        await page.wait_for_timeout(2000)
                        console.print(".", end="", flush=True)
                    
                    console.print("\n✅ Verification completed!")
                    continue
                
                # If still on login page, there might be an error
                if 'login' in current_url.lower():
                    console.print(f"⚠️ Still on login page after {i+1} seconds...")
                    
                    # Check for error messages
                    try:
                        error_element = await page.query_selector('.form__label--error, .alert, .error')
                        if error_element:
                            error_text = await error_element.inner_text()
                            console.print(f"❌ Login error detected: {error_text}")
                            self.update_progress_table(table, "🔐 LinkedIn Login", "❌ Failed", f"Login error: {error_text}")
                            return False
                    except:
                        pass
            
            # If we get here, login might have succeeded but URL check failed
            console.print("⚠️ Login status unclear, attempting to continue...")
            return True
            
        except Exception as e:
            self.update_progress_table(table, "🔐 LinkedIn Login", "❌ Failed", f"Login failed: {str(e)}")
            console.print(f"❌ Login error: {e}")
            return False
    
    async def search_jobs(self, page: Page, table: Table, keywords: str = "Python Developer", location: str = "Remote"):
        """Automated job search with visual progress"""
        self.update_progress_table(table, "🔍 Job Search", "Starting", f"Searching for '{keywords}' in '{location}'")
        
        # Navigate to jobs page
        await page.goto('https://www.linkedin.com/jobs/', timeout=30000)
        await page.wait_for_timeout(2000)
        await self.take_screenshot(page, "jobs_page")
        
        # Find and fill search keywords
        try:
            keywords_input = page.locator('input[aria-label*="Search by title"], input[placeholder*="Search by title"]').first
            await keywords_input.click()
            await keywords_input.fill(keywords)
            await page.wait_for_timeout(1000)
            
            self.update_progress_table(table, "🔍 Job Search", "Typing", f"Entered keywords: {keywords}")
            
            # Find and fill location
            location_input = page.locator('input[aria-label*="City"], input[placeholder*="City"]').first
            await location_input.click()
            await location_input.clear()
            await location_input.fill(location)
            await page.wait_for_timeout(1000)
            
            self.update_progress_table(table, "🔍 Job Search", "Typing", f"Entered location: {location}")
            
            # Submit search
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
            
            # Wait for results to load
            await page.wait_for_selector('[data-testid="job-card"], .jobs-search-results__list-item', timeout=10000)
            await self.take_screenshot(page, "search_results")
            
            self.update_progress_table(table, "🔍 Job Search", "✅ Complete", "Job search results loaded")
            return True
            
        except Exception as e:
            self.update_progress_table(table, "🔍 Job Search", "❌ Failed", f"Search failed: {str(e)}")
            return False
    
    async def extract_jobs(self, page: Page, table: Table, max_jobs: int = 10):
        """Extract job data with automation"""
        self.update_progress_table(table, "📊 Data Extraction", "Starting", f"Extracting up to {max_jobs} jobs")
        
        jobs_data = []
        
        # Scroll to load more jobs
        self.update_progress_table(table, "📊 Data Extraction", "Scrolling", "Loading more job listings")
        
        for i in range(3):  # Scroll 3 times to load more jobs
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            console.print(f"📜 Scroll {i+1}/3 completed")
        
        # Find job cards
        job_cards = await page.query_selector_all('[data-testid="job-card"], .jobs-search-results__list-item, .job-search-card')
        
        self.update_progress_table(table, "📊 Data Extraction", "Processing", f"Found {len(job_cards)} job cards")
        
        for i, card in enumerate(job_cards[:max_jobs]):
            try:
                # Extract job data
                job_data = {}
                
                # Get job title
                title_element = await card.query_selector('h3, .job-card-list__title, [data-testid="job-title"]')
                if title_element:
                    job_data['title'] = await title_element.inner_text()
                
                # Get company name
                company_element = await card.query_selector('.job-card-container__primary-description, .job-card-list__company, [data-testid="job-company"]')
                if company_element:
                    job_data['company'] = await company_element.inner_text()
                
                # Get location
                location_element = await card.query_selector('.job-card-container__metadata-item, [data-testid="job-location"]')
                if location_element:
                    job_data['location'] = await location_element.inner_text()
                
                # Get job URL
                link_element = await card.query_selector('a[href*="/jobs/view/"]')
                if link_element:
                    job_data['url'] = await link_element.get_attribute('href')
                    if job_data['url'] and not job_data['url'].startswith('http'):
                        job_data['url'] = f"https://linkedin.com{job_data['url']}"
                
                if job_data.get('title'):
                    jobs_data.append(job_data)
                    console.print(f"✅ Extracted job {i+1}: {job_data.get('title', 'Unknown')} at {job_data.get('company', 'Unknown')}")
                
            except Exception as e:
                console.print(f"⚠️ Error extracting job {i+1}: {e}")
                continue
        
        self.jobs_found = jobs_data
        self.update_progress_table(table, "📊 Data Extraction", "✅ Complete", f"Extracted {len(jobs_data)} jobs successfully")
        
        return jobs_data
    
    async def demonstrate_easy_apply(self, page: Page, table: Table, max_applications: int = 2):
        """Demonstrate Easy Apply automation (DEMO MODE - no actual applications)"""
        self.update_progress_table(table, "🚀 Auto Apply Demo", "Starting", "Demonstrating Easy Apply automation")
        
        if not self.jobs_found:
            self.update_progress_table(table, "🚀 Auto Apply Demo", "⚠️ Skipped", "No jobs found to apply to")
            return
        
        applied_count = 0
        
        for job in self.jobs_found[:max_applications]:
            if not job.get('url'):
                continue
                
            try:
                # Navigate to job posting
                await page.goto(job['url'], timeout=15000)
                await page.wait_for_timeout(2000)
                
                # Look for Easy Apply button
                easy_apply_button = await page.query_selector('button:has-text("Easy Apply")')
                
                if easy_apply_button:
                    self.update_progress_table(table, "🚀 Auto Apply Demo", "Found Easy Apply", f"Job: {job.get('title', 'Unknown')}")
                    
                    # DEMO MODE - Show what would happen but don't actually apply
                    console.print(f"\n🎯 DEMO: Would apply to {job.get('title')} at {job.get('company')}")
                    console.print("📝 DEMO: Would fill application form automatically")
                    console.print("✉️ DEMO: Would submit application")
                    console.print("⚠️ DEMO MODE: No actual application submitted for safety")
                    
                    # Simulate application process
                    await page.wait_for_timeout(2000)
                    applied_count += 1
                    
                    # Take screenshot for documentation
                    await self.take_screenshot(page, f"easy_apply_demo_{applied_count}")
                    
                else:
                    console.print(f"⚠️ No Easy Apply found for {job.get('title', 'Unknown')}")
                    
            except Exception as e:
                console.print(f"❌ Error processing {job.get('title', 'Unknown')}: {e}")
                continue
        
        self.update_progress_table(table, "🚀 Auto Apply Demo", "✅ Complete", f"Demo completed for {applied_count} jobs")
    
    async def display_results(self, table: Table):
        """Display final results"""
        self.update_progress_table(table, "📈 Results Summary", "Generating", "Compiling automation results")
        
        # Create results table
        results_table = Table(title="🎯 LinkedIn Automation Results", show_header=True, header_style="bold magenta")
        results_table.add_column("Job Title", style="cyan", width=30)
        results_table.add_column("Company", style="green", width=20)
        results_table.add_column("Location", style="yellow", width=15)
        results_table.add_column("Status", style="blue", width=15)
        
        for job in self.jobs_found:
            results_table.add_row(
                job.get('title', 'Unknown')[:30],
                job.get('company', 'Unknown')[:20],
                job.get('location', 'Unknown')[:15],
                "✅ Extracted"
            )
        
        console.print("\n")
        console.print(results_table)
        console.print("\n")
        
        # Summary stats
        summary = Panel(
            f"🎯 **Automation Summary**\n\n"
            f"✅ Jobs Found: {len(self.jobs_found)}\n"
            f"🤖 Automation Steps: Completed\n"
            f"📊 Data Extracted: {len(self.jobs_found)} job records\n"
            f"📸 Screenshots: Saved to {self.screenshot_dir}\n"
            f"🚀 Demo Mode: Safe automation demonstration",
            title="🏆 Results",
            border_style="green"
        )
        
        console.print(summary)
        self.update_progress_table(table, "📈 Results Summary", "✅ Complete", f"Found {len(self.jobs_found)} jobs with full automation")

async def main():
    """Run the LinkedIn automation demo"""
    console.print(Panel.fit("🚀 LinkedIn Job Application Agent - Live Automation Demo\nInspired by Suna AI", style="bold blue"))
    
    demo = LinkedInAutomationDemo()
    layout, progress_table = await demo.create_progress_display()
    
    browser = None
    
    try:
        # Setup browser
        console.print("🌐 Setting up browser...")
        browser, page = await demo.setup_browser()
        console.print("✅ Browser setup completed!")
        
        # Start live display
        with Live(layout, console=console, refresh_per_second=4):
            # Step 1: Login
            console.print("\n🔐 Starting LinkedIn login...")
            login_success = await demo.linkedin_login(page, progress_table)
            
            if not login_success:
                console.print("❌ Login failed. Demo cannot continue.")
                return
            
            console.print("✅ Login completed successfully!")
            
            # Step 2: Search for jobs
            console.print("\n🔍 Starting job search...")
            search_success = await demo.search_jobs(page, progress_table, "Python Developer", "Remote")
            
            if not search_success:
                console.print("⚠️ Job search failed, but continuing with demo...")
                # Continue anyway for demo purposes
            else:
                console.print("✅ Job search completed!")
            
            # Step 3: Extract job data
            console.print("\n📊 Starting job data extraction...")
            try:
                jobs = await demo.extract_jobs(page, progress_table, max_jobs=10)
                console.print(f"✅ Extracted {len(jobs)} jobs successfully!")
            except Exception as e:
                console.print(f"⚠️ Job extraction error: {e}")
                jobs = []
            
            # Step 4: Demonstrate Easy Apply (DEMO MODE)
            console.print("\n🚀 Starting Easy Apply demo...")
            try:
                await demo.demonstrate_easy_apply(page, progress_table, max_applications=2)
                console.print("✅ Easy Apply demo completed!")
            except Exception as e:
                console.print(f"⚠️ Easy Apply demo error: {e}")
            
            # Step 5: Display results
            console.print("\n📈 Generating results...")
            try:
                await demo.display_results(progress_table)
                console.print("✅ Results displayed!")
            except Exception as e:
                console.print(f"⚠️ Results display error: {e}")
        
        # Keep browser open for inspection
        console.print("\n🎯 Demo completed! Browser will stay open for 30 seconds for inspection.")
        console.print("🔍 You can manually navigate and see the automation results.")
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        console.print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        console.print(f"\n❌ Demo error: {e}")
        import traceback
        console.print(f"🔍 Full error details:\n{traceback.format_exc()}")
    finally:
        if browser:
            try:
                console.print("🔄 Closing browser...")
                await browser.close()
                console.print("✅ Browser closed successfully")
            except Exception as e:
                console.print(f"⚠️ Error closing browser: {e}")

if __name__ == "__main__":
    console.print("🚀 Starting LinkedIn Automation Demo...")
    asyncio.run(main()) 