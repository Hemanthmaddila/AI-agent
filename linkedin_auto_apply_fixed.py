#!/usr/bin/env python3
"""
🎯 LinkedIn Auto-Apply - FIXED VERSION
Main Goal: Automatically apply for jobs using WORKING extraction method
Based on successful linkedin_final_demo.py extraction
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

class LinkedInAutoApplyFixed:
    """Working LinkedIn auto-apply using proven extraction methods"""
    
    def __init__(self):
        self.session_file = "data/linkedin_session.json"
        self.screenshot_dir = "data/screenshots"
        self.applications_log = "data/applications_submitted.json"
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        # Application settings
        self.max_applications = 5  # Safety limit
        self.applications_submitted = 0
        
        # Proven working selectors from linkedin_final_demo.py
        self.working_selectors = {
            "job_id_elements": '[data-occludable-job-id], [data-job-id]',
            "easy_apply_buttons": [
                'button[aria-label*="Easy Apply"]',
                'button:has-text("Easy Apply")',
                '.jobs-apply-button',
                '[data-control-name*="jobdetails_topcard_inapply"]'
            ],
            "job_title": '.job-details-jobs-unified-top-card__job-title, h1',
            "company": '.job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name'
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
            headless=False,  # Keep visible for applications
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
        """Smart login with session management"""
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
    
    async def navigate_to_jobs_and_extract(self, page):
        """Navigate to jobs and extract using PROVEN method"""
        console.print("🔍 Navigating to LinkedIn Jobs with proven extraction...")
        
        # Use working job search URL
        search_url = "https://www.linkedin.com/jobs/search/?keywords=Python%20Developer&location=Remote&f_AL=true&f_TPR=r86400"
        console.print(f"🌐 Using: {search_url}")
        
        await page.goto(search_url)
        await page.wait_for_timeout(5000)
        
        # Aggressive scrolling (proven method)
        console.print("📜 Loading jobs with aggressive scrolling...")
        for i in range(8):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
            console.print(f"   Scroll {i+1}/8")
        
        # Extract jobs using proven method
        console.print("🎯 Extracting jobs using PROVEN data-attribute method...")
        
        jobs_with_ids = await page.query_selector_all(self.working_selectors["job_id_elements"])
        console.print(f"📊 Found {len(jobs_with_ids)} elements with job IDs")
        
        jobs_to_apply = []
        
        for element in jobs_with_ids:
            try:
                # Extract job ID
                job_id = await element.evaluate("""
                    (el) => el.getAttribute('data-occludable-job-id') || 
                           el.getAttribute('data-job-id') || ''
                """)
                
                if job_id:
                    # Click on the element to load job details
                    await element.click()
                    await page.wait_for_timeout(2000)
                    
                    # Extract job details
                    title_elem = await page.query_selector(self.working_selectors["job_title"])
                    company_elem = await page.query_selector(self.working_selectors["company"])
                    
                    title = "Unknown Title"
                    company = "Unknown Company"
                    
                    if title_elem:
                        title = (await title_elem.inner_text()).strip()
                    if company_elem:
                        company = (await company_elem.inner_text()).strip()
                    
                    # Check for Easy Apply button
                    easy_apply_btn = None
                    for btn_selector in self.working_selectors["easy_apply_buttons"]:
                        btn = await page.query_selector(btn_selector)
                        if btn:
                            easy_apply_btn = btn
                            console.print(f"✅ Easy Apply: {title[:30]} at {company[:20]}")
                            break
                    
                    if easy_apply_btn and title != "Unknown Title":
                        jobs_to_apply.append({
                            'job_id': job_id,
                            'title': title,
                            'company': company,
                            'easy_apply_button': easy_apply_btn,
                            'url': page.url
                        })
                        
                        # Limit to prevent overwhelming
                        if len(jobs_to_apply) >= 10:
                            break
            
            except Exception as e:
                console.print(f"⚠️ Error processing element: {e}")
                continue
        
        console.print(f"🎯 Found {len(jobs_to_apply)} jobs ready for Easy Apply!")
        return jobs_to_apply
    
    async def apply_to_job(self, page, job_info):
        """Apply to a single job using Easy Apply"""
        try:
            console.print(f"📝 APPLYING: {job_info['title'][:40]} at {job_info['company'][:25]}")
            
            # Navigate to job if needed
            if job_info['url'] not in page.url:
                await page.goto(job_info['url'])
                await page.wait_for_timeout(3000)
            
            # Find and click Easy Apply button
            easy_apply_btn = None
            for btn_selector in self.working_selectors["easy_apply_buttons"]:
                btn = await page.query_selector(btn_selector)
                if btn:
                    easy_apply_btn = btn
                    break
            
            if not easy_apply_btn:
                console.print("❌ Easy Apply button not found")
                return False
            
            # Click Easy Apply
            await easy_apply_btn.click()
            await page.wait_for_timeout(3000)
            
            # Handle Easy Apply modal
            modal_selectors = ['.jobs-easy-apply-modal', '.artdeco-modal', '[role="dialog"]']
            modal = None
            
            for modal_sel in modal_selectors:
                modal = await page.query_selector(modal_sel)
                if modal:
                    break
            
            if not modal:
                console.print("❌ Easy Apply modal not found")
                return False
            
            console.print("✅ Easy Apply modal opened")
            
            # Fill basic form fields if needed
            await self.fill_application_form(page, modal)
            
            # Look for Submit button
            submit_selectors = [
                'button[aria-label*="Submit application"]',
                'button:has-text("Submit application")',
                'button:has-text("Apply")',
                'button[type="submit"]'
            ]
            
            submit_btn = None
            for submit_sel in submit_selectors:
                btn = await modal.query_selector(submit_sel)
                if btn:
                    submit_btn = btn
                    break
            
            if not submit_btn:
                console.print("❌ Submit button not found")
                # Close modal
                close_btn = await modal.query_selector('button[aria-label*="Dismiss"], .artdeco-modal__dismiss')
                if close_btn:
                    await close_btn.click()
                return False
            
            # Safety check before submitting
            if self.applications_submitted >= self.max_applications:
                console.print("⚠️ Reached maximum applications limit")
                return False
            
            # Final confirmation
            console.print(f"\n🚀 READY TO SUBMIT APPLICATION:")
            console.print(f"   Job: {job_info['title']}")
            console.print(f"   Company: {job_info['company']}")
            console.print(f"   Applications so far: {self.applications_submitted}")
            
            if Confirm.ask(f"🔥 Submit this application?"):
                await submit_btn.click()
                await page.wait_for_timeout(3000)
                
                # Log the application
                await self.log_application(job_info)
                self.applications_submitted += 1
                
                console.print(f"✅ APPLICATION SUBMITTED! ({self.applications_submitted}/{self.max_applications})")
                await page.screenshot(path=f'{self.screenshot_dir}/application_{self.applications_submitted}.png')
                
                return True
            else:
                console.print("⏭️ Application skipped")
                # Close modal
                close_btn = await modal.query_selector('button[aria-label*="Dismiss"], .artdeco-modal__dismiss')
                if close_btn:
                    await close_btn.click()
                return False
                
        except Exception as e:
            console.print(f"❌ Error applying: {e}")
            return False
    
    async def fill_application_form(self, page, modal):
        """Fill basic application form fields"""
        try:
            # Phone number
            phone_input = await modal.query_selector('input[id*="phone"], input[name*="phone"]')
            if phone_input:
                phone = input("📞 Phone number (optional): ").strip()
                if phone:
                    await phone_input.fill(phone)
            
            # Cover letter
            cover_textarea = await modal.query_selector('textarea')
            if cover_textarea:
                cover_letter = input("📝 Cover letter (optional): ").strip()
                if cover_letter:
                    await cover_textarea.fill(cover_letter)
            
            console.print("📝 Form fields filled")
            
        except Exception as e:
            console.print(f"⚠️ Error filling form: {e}")
    
    async def log_application(self, job_info):
        """Log submitted application"""
        try:
            import datetime
            
            log_entry = {
                'job_id': job_info['job_id'],
                'title': job_info['title'],
                'company': job_info['company'],
                'url': job_info['url'],
                'timestamp': datetime.datetime.now().isoformat(),
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
            console.print(f"⚠️ Error logging: {e}")

async def main():
    """Main function: Auto-apply using WORKING extraction method"""
    console.print("🎯 LinkedIn Auto-Apply - FIXED VERSION")
    console.print("="*60)
    console.print("🔧 Using PROVEN job extraction method")
    console.print("🚀 Main Goal: Automatically apply for jobs")
    console.print("="*60)
    
    auto_apply = LinkedInAutoApplyFixed()
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
        console.print(f"\n⚠️ SAFETY CHECK:")
        console.print(f"   Max applications: {auto_apply.max_applications}")
        console.print(f"   Will require confirmation for each application")
        console.print(f"   Real applications will be submitted")
        
        if not Confirm.ask("🔥 Ready to start AUTO-APPLYING for jobs?"):
            console.print("⏹️ Auto-apply cancelled")
            return
        
        # Extract jobs using proven method
        jobs_to_apply = await auto_apply.navigate_to_jobs_and_extract(page)
        
        if not jobs_to_apply:
            console.print("⚠️ No Easy Apply jobs found")
            console.print("💡 Try different search criteria")
            return
        
        # Display found jobs
        table = Table(title="🎯 Easy Apply Jobs Found", show_header=True)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Job Title", style="green", width=35)
        table.add_column("Company", style="yellow", width=25)
        table.add_column("Job ID", style="blue", width=15)
        
        for i, job in enumerate(jobs_to_apply, 1):
            table.add_row(
                str(i),
                job['title'][:32] + "..." if len(job['title']) > 35 else job['title'],
                job['company'][:22] + "..." if len(job['company']) > 25 else job['company'],
                job['job_id'][:12] + "..." if len(job['job_id']) > 15 else job['job_id']
            )
        
        console.print(table)
        
        # Apply to jobs
        console.print(f"\n🚀 Starting auto-apply process...")
        successful_applications = 0
        
        for i, job in enumerate(jobs_to_apply):
            if auto_apply.applications_submitted >= auto_apply.max_applications:
                console.print("⚠️ Reached application limit")
                break
            
            console.print(f"\n📋 Job {i+1}/{len(jobs_to_apply)}:")
            
            success = await auto_apply.apply_to_job(page, job)
            if success:
                successful_applications += 1
            
            # Human-like delay
            if i < len(jobs_to_apply) - 1:  # Don't wait after last job
                await asyncio.sleep(random.randint(5, 10))
        
        # Final summary
        console.print("\n🎉 AUTO-APPLY SESSION COMPLETE!")
        console.print("="*50)
        console.print(f"✅ Applications submitted: {successful_applications}")
        console.print(f"📊 Total jobs found: {len(jobs_to_apply)}")
        console.print(f"📈 Success rate: {(successful_applications/len(jobs_to_apply)*100):.1f}%")
        console.print(f"📁 Screenshots: {auto_apply.screenshot_dir}")
        console.print(f"📝 Applications log: {auto_apply.applications_log}")
        
        console.print(f"\n🎯 MISSION STATUS:")
        if successful_applications > 0:
            console.print(f"✅ SUCCESS! You have automatically applied to {successful_applications} jobs!")
            console.print(f"🚀 Your LinkedIn auto-apply system is working!")
        else:
            console.print(f"⚠️ No applications submitted (user cancelled or errors)")
        
        # Keep browser open briefly
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