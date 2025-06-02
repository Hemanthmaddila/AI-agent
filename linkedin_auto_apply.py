#!/usr/bin/env python3
"""
🎯 LinkedIn Auto-Apply - MAIN GOAL: Automatically Apply for Jobs
Focus on the core functionality: Finding jobs and clicking Apply
"""

import asyncio
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

class LinkedInAutoApply:
    """Main goal: Automatically apply for jobs on LinkedIn"""
    
    def __init__(self):
        self.screenshot_dir = "data/screenshots"
        self.session_file = "data/linkedin_session.json"
        self.applications_log = "data/applications_submitted.json"
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        # Application settings
        self.max_applications = 10  # Safety limit
        self.applications_submitted = 0
        self.target_keywords = ["Python Developer", "Software Engineer", "AI Engineer", "Machine Learning"]
        self.target_locations = ["Remote", "United States"]
    
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
            headless=False,  # Keep visible for safety
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-dev-shm-usage'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Hide automation
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            window.chrome = { runtime: {} };
        """)
        
        return browser, page
    
    async def login_if_needed(self, page, context):
        """Smart login with session management"""
        # Try existing session first
        if await self.load_session(context):
            console.print("🔍 Testing existing session...")
            await page.goto('https://www.linkedin.com/feed/')
            await page.wait_for_timeout(3000)
            
            if any(indicator in page.url for indicator in ['/feed', '/in/']):
                console.print("✅ Session restored! Skipping login.")
                return True
        
        # Need fresh login
        console.print("🔐 LinkedIn login required...")
        await page.goto('https://www.linkedin.com/login')
        await page.wait_for_selector('#username')
        
        email = Prompt.ask("📧 LinkedIn Email")
        password = Prompt.ask("🔒 Password", password=True)
        
        # Human-like login
        await page.type('#username', email, delay=random.randint(50, 150))
        await page.wait_for_timeout(random.randint(500, 1000))
        
        await page.type('#password', password, delay=random.randint(50, 150))
        await page.wait_for_timeout(random.randint(500, 1000))
        
        await page.click('button[type="submit"]')
        
        # Wait for login success
        for i in range(20):
            await page.wait_for_timeout(1000)
            if any(indicator in page.url for indicator in ['/feed', '/in/']):
                console.print("✅ Login successful!")
                await self.save_session(context)
                return True
            
            if any(challenge in page.url for challenge in ['challenge', 'checkpoint']):
                console.print("🤖 Please complete verification manually...")
                input("Press Enter when verification is complete...")
                continue
        
        return True
    
    async def search_for_jobs(self, page):
        """Search for jobs with target keywords"""
        console.print("🔍 Searching for target jobs...")
        
        # Use job search with specific criteria
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={self.target_keywords[0]}&location={self.target_locations[0]}&f_TPR=r86400&f_AL=true"
        
        await page.goto(search_url)
        await page.wait_for_timeout(5000)
        
        # Scroll to load more jobs
        for i in range(3):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
        
        console.print("✅ Job search completed")
        await page.screenshot(path=f'{self.screenshot_dir}/job_search_page.png')
        return True
    
    async def find_easy_apply_jobs(self, page):
        """Find jobs with Easy Apply button"""
        console.print("🎯 Looking for Easy Apply jobs...")
        
        # Look for Easy Apply buttons
        easy_apply_selectors = [
            'button[aria-label*="Easy Apply"]',
            'button:has-text("Easy Apply")',
            '.jobs-apply-button--top-card',
            '[data-control-name="jobdetails_topcard_inapply"]'
        ]
        
        jobs_to_apply = []
        
        # Find job cards with Easy Apply
        job_cards = await page.query_selector_all('[data-occludable-job-id], .job-card-container')
        console.print(f"📊 Found {len(job_cards)} job cards to check...")
        
        for i, card in enumerate(job_cards[:20]):  # Check first 20 jobs
            try:
                # Click on the job to see details
                await card.click()
                await page.wait_for_timeout(2000)
                
                # Check for Easy Apply button
                easy_apply_btn = None
                for selector in easy_apply_selectors:
                    btn = await page.query_selector(selector)
                    if btn:
                        easy_apply_btn = btn
                        break
                
                if easy_apply_btn:
                    # Get job details
                    title = "Unknown"
                    company = "Unknown"
                    
                    try:
                        title_elem = await page.query_selector('h1, .job-details-jobs-unified-top-card__job-title')
                        if title_elem:
                            title = await title_elem.inner_text()
                        
                        company_elem = await page.query_selector('.job-details-jobs-unified-top-card__company-name')
                        if company_elem:
                            company = await company_elem.inner_text()
                    except:
                        pass
                    
                    jobs_to_apply.append({
                        'title': title.strip()[:60],
                        'company': company.strip()[:40],
                        'easy_apply_button': easy_apply_btn,
                        'card_index': i
                    })
                    console.print(f"✅ Easy Apply available: {title[:30]} at {company[:20]}")
                
            except Exception as e:
                console.print(f"⚠️ Error checking job {i+1}: {e}")
                continue
        
        console.print(f"🎯 Found {len(jobs_to_apply)} jobs with Easy Apply!")
        return jobs_to_apply
    
    async def apply_to_job(self, page, job_info):
        """Apply to a single job using Easy Apply"""
        try:
            console.print(f"📝 Applying to: {job_info['title']} at {job_info['company']}")
            
            # Click Easy Apply button
            await job_info['easy_apply_button'].click()
            await page.wait_for_timeout(3000)
            
            # Handle the Easy Apply modal
            modal_selectors = ['.jobs-easy-apply-modal', '.jobs-easy-apply-content']
            modal = None
            for selector in modal_selectors:
                modal = await page.query_selector(selector)
                if modal:
                    break
            
            if not modal:
                console.print("❌ Easy Apply modal not found")
                return False
            
            # Look for form fields to fill
            await self.fill_application_form(page, modal)
            
            # Look for Submit/Apply button
            submit_selectors = [
                'button[aria-label*="Submit application"]',
                'button:has-text("Submit application")',
                'button:has-text("Apply")',
                '.jobs-apply-button'
            ]
            
            submit_btn = None
            for selector in submit_selectors:
                btn = await modal.query_selector(selector)
                if btn:
                    submit_btn = btn
                    break
            
            if submit_btn:
                # Safety check before submitting
                if self.applications_submitted >= self.max_applications:
                    console.print("⚠️ Reached maximum applications limit for safety")
                    return False
                
                # Ask for confirmation in production mode
                if Confirm.ask(f"🚀 Submit application to {job_info['company']}?"):
                    await submit_btn.click()
                    await page.wait_for_timeout(3000)
                    
                    # Log the application
                    await self.log_application(job_info)
                    self.applications_submitted += 1
                    
                    console.print(f"✅ Application submitted! ({self.applications_submitted}/{self.max_applications})")
                    await page.screenshot(path=f'{self.screenshot_dir}/application_{self.applications_submitted}.png')
                    return True
                else:
                    console.print("⏭️ Skipping application")
                    return False
            else:
                console.print("❌ Submit button not found")
                return False
                
        except Exception as e:
            console.print(f"❌ Error applying to job: {e}")
            return False
    
    async def fill_application_form(self, page, modal):
        """Fill out application form fields"""
        try:
            # Look for common form fields
            phone_input = await modal.query_selector('input[id*="phone"], input[name*="phone"]')
            if phone_input:
                phone = Prompt.ask("📞 Phone number (optional)", default="")
                if phone:
                    await phone_input.fill(phone)
            
            # Handle cover letter
            cover_letter = await modal.query_selector('textarea')
            if cover_letter:
                cover_text = Prompt.ask("📝 Cover letter (optional)", default="")
                if cover_text:
                    await cover_letter.fill(cover_text)
            
            # Handle dropdowns (experience level, etc.)
            selects = await modal.query_selector_all('select')
            for select in selects:
                # For now, just select the first option
                await select.select_option(index=0)
                
            console.print("📝 Form fields filled")
            
        except Exception as e:
            console.print(f"⚠️ Error filling form: {e}")
    
    async def log_application(self, job_info):
        """Log submitted application"""
        try:
            log_entry = {
                'title': job_info['title'],
                'company': job_info['company'],
                'timestamp': str(asyncio.get_event_loop().time()),
                'status': 'submitted'
            }
            
            # Load existing log
            applications = []
            if Path(self.applications_log).exists():
                with open(self.applications_log, 'r') as f:
                    applications = json.load(f)
            
            applications.append(log_entry)
            
            # Save updated log
            with open(self.applications_log, 'w') as f:
                json.dump(applications, f, indent=2)
                
        except Exception as e:
            console.print(f"⚠️ Error logging application: {e}")

async def main():
    """Main function: Auto-apply for LinkedIn jobs"""
    console.print("🎯 LinkedIn Auto-Apply - MAIN GOAL: Job Applications")
    console.print("="*60)
    console.print("🚀 Goal: Automatically find and apply for relevant jobs")
    console.print("="*60)
    
    auto_apply = LinkedInAutoApply()
    browser = None
    
    try:
        # Setup
        browser, page = await auto_apply.setup_browser()
        context = page.context
        
        # Login
        if not await auto_apply.login_if_needed(page, context):
            console.print("❌ Login failed")
            return
        
        console.print("🎉 LinkedIn authentication successful!")
        
        # Safety confirmation
        if not Confirm.ask("🔥 Ready to start AUTO-APPLYING for jobs? (This will submit real applications)"):
            console.print("⏹️ Auto-apply cancelled for safety")
            return
        
        # Search for jobs
        await auto_apply.search_for_jobs(page)
        
        # Find Easy Apply jobs
        jobs_to_apply = await auto_apply.find_easy_apply_jobs(page)
        
        if not jobs_to_apply:
            console.print("⚠️ No Easy Apply jobs found. Try different search criteria.")
            return
        
        # Display jobs found
        table = Table(title="🎯 Jobs Found with Easy Apply", show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Job Title", style="green", width=40)
        table.add_column("Company", style="yellow", width=30)
        
        for i, job in enumerate(jobs_to_apply, 1):
            table.add_row(str(i), job['title'], job['company'])
        
        console.print(table)
        
        # Apply to jobs
        console.print(f"\n🚀 Starting auto-apply process for {len(jobs_to_apply)} jobs...")
        
        successful_applications = 0
        for job in jobs_to_apply:
            if auto_apply.applications_submitted >= auto_apply.max_applications:
                console.print("⚠️ Reached application limit for safety")
                break
            
            success = await auto_apply.apply_to_job(page, job)
            if success:
                successful_applications += 1
            
            # Human-like delay between applications
            await asyncio.sleep(random.randint(10, 20))
        
        # Final summary
        console.print("\n🎉 AUTO-APPLY SESSION COMPLETE!")
        console.print("="*50)
        console.print(f"✅ Applications submitted: {successful_applications}")
        console.print(f"📊 Success rate: {(successful_applications/len(jobs_to_apply)*100):.1f}%")
        console.print(f"📁 Screenshots saved: {auto_apply.screenshot_dir}")
        console.print(f"📝 Applications log: {auto_apply.applications_log}")
        
        await asyncio.sleep(10)
        
    except Exception as e:
        console.print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if browser:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 