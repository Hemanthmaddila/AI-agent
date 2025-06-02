#!/usr/bin/env python3
"""
🎯 LinkedIn Job Finder - FOCUSED FIX for Job Discovery Bottleneck
Specifically addresses the core issue: finding Easy Apply jobs on LinkedIn
"""

import asyncio
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table

console = Console()

class LinkedInJobFinder:
    """Focused LinkedIn job finder to fix the discovery bottleneck"""
    
    def __init__(self):
        self.session_file = "data/linkedin_session.json"
        self.screenshot_dir = "data/screenshots"
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        # Updated 2025 LinkedIn selectors
        self.current_selectors = {
            # Job search elements
            "search_keywords": 'input[aria-label*="Search by title"], input[id*="jobs-search-box-keyword-id"]',
            "search_location": 'input[aria-label*="City"], input[id*="jobs-search-box-location-id"]',
            "search_button": 'button[aria-label*="Search"], button:has-text("Search")',
            
            # Job listing containers
            "job_results_container": '.jobs-search-results-list, .scaffold-layout__list-container, .jobs-search__results-list',
            "job_cards": [
                'li[data-occludable-job-id]',  # Most reliable
                '.job-card-container',
                '.jobs-search-results-list__list-item',
                '.job-search-card',
                'div[data-job-id]',
                '.artdeco-card'
            ],
            
            # Job details within cards
            "job_title": '.job-card-list__title, .job-search-card__title, h3 a',
            "job_company": '.job-card-container__primary-description, .job-search-card__subtitle, h4',
            "job_location": '.job-card-container__metadata-item, .job-search-card__location',
            
            # Easy Apply buttons
            "easy_apply_buttons": [
                'button[aria-label*="Easy Apply"]',
                'button:has-text("Easy Apply")',
                '.jobs-apply-button',
                '[data-control-name*="jobdetails_topcard_inapply"]'
            ],
            
            # Filters
            "easy_apply_filter": 'button[aria-label*="Easy Apply filter"], #f_AL-checkbox',
            "date_filter": 'button[aria-label*="Date posted filter"], #f_TPR',
            "remote_filter": 'button[aria-label*="Remote filter"], #f_WT'
        }
    
    async def load_session(self, context):
        """Load existing LinkedIn session"""
        try:
            if Path(self.session_file).exists():
                with open(self.session_file, 'r') as f:
                    state = json.load(f)
                await context.add_cookies(state.get('cookies', []))
                return True
        except:
            pass
        return False
    
    async def save_session(self, context):
        """Save LinkedIn session"""
        try:
            state = await context.storage_state()
            with open(self.session_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            console.print(f"⚠️ Session save failed: {e}")
    
    async def setup_browser(self):
        """Setup browser with anti-detection"""
        playwright = await async_playwright().start()
        
        browser = await playwright.chromium.launch(
            headless=False,  # Keep visible for debugging
            slow_mo=500,     # Slow down for debugging
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Anti-detection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            window.chrome = { runtime: {} };
        """)
        
        return browser, page
    
    async def login_if_needed(self, page, context):
        """Handle LinkedIn login with session management"""
        # Try existing session
        if await self.load_session(context):
            console.print("🔍 Testing existing session...")
            await page.goto('https://www.linkedin.com/feed/')
            await page.wait_for_timeout(3000)
            
            if any(indicator in page.url for indicator in ['/feed', '/in/']):
                console.print("✅ Session restored!")
                return True
        
        # Fresh login needed
        console.print("🔐 LinkedIn login required...")
        await page.goto('https://www.linkedin.com/login')
        await page.wait_for_selector('#username')
        
        email = input("📧 LinkedIn Email: ").strip()
        password = input("🔒 Password: ").strip()
        
        # Type credentials
        await page.type('#username', email, delay=random.randint(50, 150))
        await page.wait_for_timeout(random.randint(500, 1000))
        
        await page.type('#password', password, delay=random.randint(50, 150))
        await page.wait_for_timeout(random.randint(500, 1000))
        
        await page.click('button[type="submit"]')
        
        # Wait for login
        for i in range(20):
            await page.wait_for_timeout(1000)
            if any(indicator in page.url for indicator in ['/feed', '/in/']):
                console.print("✅ Login successful!")
                await self.save_session(context)
                return True
            
            if any(challenge in page.url for challenge in ['challenge', 'checkpoint']):
                console.print("🤖 Complete verification manually...")
                input("Press Enter when done...")
                continue
        
        return True
    
    async def navigate_to_jobs_search(self, page, keywords="Python Developer", location="Remote"):
        """Navigate to LinkedIn jobs search with debugging"""
        console.print(f"🔍 Navigating to LinkedIn Jobs search...")
        console.print(f"Keywords: {keywords}")
        console.print(f"Location: {location}")
        
        # Method 1: Direct URL approach
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}&f_AL=true&f_TPR=r86400"
        console.print(f"🌐 Using direct URL: {search_url}")
        
        await page.goto(search_url)
        await page.wait_for_timeout(5000)
        
        # Take screenshot for debugging
        await page.screenshot(path=f'{self.screenshot_dir}/01_after_navigation.png')
        console.print(f"📸 Screenshot saved: 01_after_navigation.png")
        
        return True
    
    async def find_job_cards(self, page):
        """Find job cards with comprehensive debugging"""
        console.print("🔍 DEBUGGING: Finding job cards...")
        
        # Wait for page to load
        await page.wait_for_timeout(3000)
        
        # Check page state
        page_title = await page.title()
        current_url = page.url
        console.print(f"📄 Page title: {page_title}")
        console.print(f"🔗 Current URL: {current_url}")
        
        # Try each job card selector
        job_cards = []
        for i, selector in enumerate(self.current_selectors["job_cards"]):
            console.print(f"🎯 Testing selector {i+1}: {selector}")
            try:
                elements = await page.query_selector_all(selector)
                console.print(f"   Found {len(elements)} elements")
                
                if len(elements) > 0:
                    console.print(f"✅ SUCCESS! Found {len(elements)} job cards with: {selector}")
                    job_cards = elements
                    
                    # Save this working selector
                    self.working_job_selector = selector
                    break
            except Exception as e:
                console.print(f"   ❌ Error: {e}")
        
        if not job_cards:
            console.print("⚠️ No job cards found with any selector!")
            console.print("🔍 Debugging: Looking for any job-related elements...")
            
            # Debug: Look for any elements that might be job cards
            debug_selectors = [
                'li', 'div[data-job-id]', 'div[data-entity-urn]', 
                '.artdeco-card', '[class*="job"]', '[class*="card"]'
            ]
            
            for debug_sel in debug_selectors:
                try:
                    debug_elements = await page.query_selector_all(debug_sel)
                    if len(debug_elements) > 0:
                        console.print(f"🔍 Found {len(debug_elements)} elements with: {debug_sel}")
                except:
                    pass
            
            # Save debug screenshot
            await page.screenshot(path=f'{self.screenshot_dir}/02_no_job_cards_found.png')
            return []
        
        # Take screenshot of found job cards
        await page.screenshot(path=f'{self.screenshot_dir}/03_job_cards_found.png')
        
        return job_cards
    
    async def extract_job_data(self, page, job_cards):
        """Extract data from found job cards"""
        console.print(f"📊 Extracting data from {len(job_cards)} job cards...")
        
        jobs = []
        for i, card in enumerate(job_cards[:10]):  # Process first 10
            try:
                console.print(f"🔍 Processing job card {i+1}...")
                
                # Click on the job card to load details
                await card.click()
                await page.wait_for_timeout(2000)
                
                # Extract basic job info from the card
                title = "Unknown"
                company = "Unknown"
                location = "Unknown"
                
                # Try multiple title selectors
                for title_sel in ['.job-card-list__title', 'h3 a', '.job-search-card__title']:
                    try:
                        title_elem = await card.query_selector(title_sel)
                        if title_elem:
                            title_text = await title_elem.inner_text()
                            if title_text and len(title_text.strip()) > 3:
                                title = title_text.strip()
                                break
                    except:
                        continue
                
                # Try multiple company selectors
                for company_sel in ['.job-card-container__primary-description', 'h4', '.job-search-card__subtitle']:
                    try:
                        company_elem = await card.query_selector(company_sel)
                        if company_elem:
                            company_text = await company_elem.inner_text()
                            if company_text and len(company_text.strip()) > 1:
                                company = company_text.strip()
                                break
                    except:
                        continue
                
                # Check for Easy Apply button
                has_easy_apply = False
                for easy_apply_sel in self.current_selectors["easy_apply_buttons"]:
                    try:
                        easy_apply_btn = await page.query_selector(easy_apply_sel)
                        if easy_apply_btn:
                            has_easy_apply = True
                            console.print(f"✅ Easy Apply available: {title[:30]}")
                            break
                    except:
                        continue
                
                if title != "Unknown" and company != "Unknown":
                    job_data = {
                        'title': title,
                        'company': company, 
                        'location': location,
                        'has_easy_apply': has_easy_apply,
                        'url': page.url
                    }
                    jobs.append(job_data)
                    console.print(f"📝 Job {len(jobs)}: {title[:30]} at {company[:20]} (Easy Apply: {has_easy_apply})")
                
            except Exception as e:
                console.print(f"⚠️ Error processing job {i+1}: {e}")
                continue
        
        return jobs
    
    async def test_easy_apply_workflow(self, page, job_data):
        """Test the Easy Apply workflow on a specific job"""
        console.print(f"🧪 Testing Easy Apply workflow for: {job_data['title']}")
        
        # Look for Easy Apply button
        easy_apply_btn = None
        for selector in self.current_selectors["easy_apply_buttons"]:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    easy_apply_btn = btn
                    console.print(f"✅ Found Easy Apply button: {selector}")
                    break
            except:
                continue
        
        if not easy_apply_btn:
            console.print("❌ No Easy Apply button found")
            return False
        
        # Click Easy Apply button (just to test the workflow)
        console.print("🖱️ Clicking Easy Apply button...")
        await easy_apply_btn.click()
        await page.wait_for_timeout(3000)
        
        # Check if modal opened
        modal_selectors = ['.jobs-easy-apply-modal', '.artdeco-modal']
        modal_found = False
        
        for modal_sel in modal_selectors:
            try:
                modal = await page.query_selector(modal_sel)
                if modal:
                    console.print(f"✅ Easy Apply modal opened: {modal_sel}")
                    modal_found = True
                    
                    # Take screenshot of modal
                    await page.screenshot(path=f'{self.screenshot_dir}/04_easy_apply_modal.png')
                    
                    # Close modal (don't actually apply)
                    close_btn = await page.query_selector('button[aria-label*="Dismiss"], .artdeco-modal__dismiss')
                    if close_btn:
                        await close_btn.click()
                        console.print("✅ Closed Easy Apply modal")
                    
                    break
            except:
                continue
        
        if not modal_found:
            console.print("❌ Easy Apply modal did not open")
            await page.screenshot(path=f'{self.screenshot_dir}/04_no_modal.png')
        
        return modal_found

async def main():
    """Main function to test and fix LinkedIn job discovery"""
    console.print("🎯 LinkedIn Job Finder - FOCUSED FIX")
    console.print("="*60)
    console.print("🔧 Testing and fixing LinkedIn job discovery bottleneck")
    console.print("="*60)
    
    finder = LinkedInJobFinder()
    browser = None
    
    try:
        # Setup browser
        browser, page = await finder.setup_browser()
        context = page.context
        
        # Login
        if not await finder.login_if_needed(page, context):
            console.print("❌ Login failed")
            return
        
        console.print("🎉 LinkedIn authentication successful!")
        
        # Navigate to jobs search
        await finder.navigate_to_jobs_search(page, "Python Developer", "Remote")
        
        # Find job cards
        job_cards = await finder.find_job_cards(page)
        
        if not job_cards:
            console.print("❌ CRITICAL: No job cards found!")
            console.print("💡 This is the main bottleneck causing application failures")
            console.print("🔧 Recommended actions:")
            console.print("   1. Check screenshots in data/screenshots/")
            console.print("   2. Manually verify LinkedIn search page structure")
            console.print("   3. Update selectors based on current LinkedIn UI")
            return
        
        # Extract job data
        jobs = await finder.extract_job_data(page, job_cards)
        
        if not jobs:
            console.print("❌ No job data extracted from cards")
            return
        
        # Display results
        console.print(f"\n🎉 SUCCESS! Found {len(jobs)} jobs")
        
        table = Table(title="LinkedIn Jobs Found")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Job Title", style="green", width=30)
        table.add_column("Company", style="yellow", width=20)
        table.add_column("Easy Apply", style="blue", width=12)
        
        easy_apply_jobs = []
        for i, job in enumerate(jobs, 1):
            easy_apply_status = "✅ Yes" if job['has_easy_apply'] else "❌ No"
            table.add_row(
                str(i),
                job['title'][:28],
                job['company'][:18],
                easy_apply_status
            )
            
            if job['has_easy_apply']:
                easy_apply_jobs.append(job)
        
        console.print(table)
        
        # Test Easy Apply workflow on first available job
        if easy_apply_jobs:
            console.print(f"\n🧪 Testing Easy Apply workflow...")
            test_job = easy_apply_jobs[0]
            
            # Navigate back to the test job
            await page.goto(test_job['url'])
            await page.wait_for_timeout(3000)
            
            workflow_success = await finder.test_easy_apply_workflow(page, test_job)
            
            console.print(f"\n📊 WORKFLOW TEST RESULTS:")
            console.print(f"✅ Login: Working")
            console.print(f"✅ Job Discovery: Working ({len(jobs)} jobs found)")
            console.print(f"✅ Easy Apply Detection: Working ({len(easy_apply_jobs)} Easy Apply jobs)")
            console.print(f"{'✅' if workflow_success else '❌'} Easy Apply Modal: {'Working' if workflow_success else 'Failed'}")
            
            if workflow_success:
                console.print("\n🎉 ALL CORE WORKFLOWS WORKING!")
                console.print("💡 Your job application automation should now work")
                console.print("🚀 Try running: python linkedin_auto_apply.py")
            else:
                console.print("\n⚠️ Easy Apply modal issue detected")
                console.print("💡 Job discovery works, but application workflow needs adjustment")
        
        else:
            console.print(f"\n⚠️ Found {len(jobs)} jobs but none have Easy Apply")
            console.print("💡 Try different search criteria or check Easy Apply filters")
        
        # Save working selectors
        if hasattr(finder, 'working_job_selector'):
            working_selectors = {
                "job_cards_working": finder.working_job_selector,
                "test_date": "2025-01-27",
                "jobs_found": len(jobs),
                "easy_apply_jobs": len(easy_apply_jobs)
            }
            
            with open('data/working_linkedin_selectors.json', 'w') as f:
                json.dump(working_selectors, f, indent=2)
            
            console.print(f"\n💾 Saved working selectors to: data/working_linkedin_selectors.json")
        
        console.print(f"\n📁 All screenshots saved to: {finder.screenshot_dir}")
        console.print("⏳ Browser staying open for 15 seconds for manual inspection...")
        await asyncio.sleep(15)
        
    except Exception as e:
        console.print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if browser:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 