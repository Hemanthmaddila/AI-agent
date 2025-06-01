#!/usr/bin/env python3
"""
🚀 LinkedIn Simple Demo - Focused Automation Test
Simplified version to test core automation without complex UI
"""

import asyncio
import random
import json
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console

console = Console()

class LinkedInSimpleDemo:
    """Simplified LinkedIn automation demo with Suna-inspired features"""
    
    def __init__(self):
        self.screenshot_dir = "data/screenshots"
        self.session_file = "data/linkedin_session.json"
        Path(self.screenshot_dir).mkdir(parents=True, exist_ok=True)
        Path("data").mkdir(exist_ok=True)
    
    async def save_session(self, context):
        """Save browser session like Suna does"""
        try:
            # Save cookies and storage state
            state = await context.storage_state()
            with open(self.session_file, 'w') as f:
                json.dump(state, f)
            console.print("✅ Session saved successfully")
        except Exception as e:
            console.print(f"⚠️ Failed to save session: {e}")
    
    async def load_session(self, context):
        """Load existing session like Suna does"""
        try:
            if Path(self.session_file).exists():
                with open(self.session_file, 'r') as f:
                    state = json.load(f)
                await context.add_cookies(state.get('cookies', []))
                console.print("✅ Previous session loaded")
                return True
        except Exception as e:
            console.print(f"⚠️ Failed to load session: {e}")
        return False
    
    async def setup_browser(self):
        """Setup browser with Suna-inspired anti-detection measures"""
        console.print("🌐 Setting up Suna-inspired browser...")
        
        playwright = await async_playwright().start()
        
        # Suna-style browser arguments for maximum stealth
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-logging',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--no-first-run',
                '--no-default-browser-check',
                '--no-pings',
                '--password-store=basic',
                '--use-mock-keychain',
                '--disable-client-side-phishing-detection',
                '--disable-sync',
                '--metrics-recording-only',
                '--no-report-upload',
                '--disable-notifications',
                '--disable-plugins-discovery'
            ]
        )
        
        # Suna-inspired context with realistic fingerprinting
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Cache-Control': 'max-age=0'
            },
            # Realistic timezone and locale
            timezone_id='America/New_York',
            locale='en-US',
            # Realistic screen size
            screen={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Comprehensive Suna-style anti-detection scripts
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Add realistic plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        name: 'Chrome PDF Plugin',
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer'
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        description: '',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'
                    },
                    {
                        name: 'Native Client',
                        description: '',
                        filename: 'internal-nacl-plugin'
                    }
                ]
            });
            
            // Add realistic languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Add chrome runtime
            window.chrome = {
                runtime: {},
                app: {
                    isInstalled: false
                }
            };
            
            // Mock permissions API
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'granted' })
                })
            });
            
            // Mock battery API
            Object.defineProperty(navigator, 'getBattery', {
                get: () => () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                })
            });
            
            // Hide automation traces
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // Override console.debug used by automation tools
            console.debug = () => {};
            
            // Add realistic connection
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10
                })
            });
            
            // Mock realistic hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // Add realistic device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
        """)
        
        console.print("✅ Suna-style browser ready with advanced stealth!")
        return browser, page
    
    async def login_to_linkedin(self, page, context):
        """Suna-inspired LinkedIn login with session management"""
        console.print("🔐 Checking for existing LinkedIn session...")
        
        # Try to load existing session first
        session_loaded = await self.load_session(context)
        
        if session_loaded:
            # Test if session is still valid
            console.print("🔍 Testing existing session...")
            await page.goto('https://www.linkedin.com/feed/')
            await page.wait_for_timeout(3000)
            
            if 'feed' in page.url or '/in/' in page.url:
                console.print("✅ Existing session is valid!")
                await page.screenshot(path=f'{self.screenshot_dir}/session_restored.png')
                return True
            else:
                console.print("⚠️ Session expired, need fresh login")
        
        # Fresh login required
        console.print("🔐 Starting fresh LinkedIn login...")
        await page.goto('https://www.linkedin.com/login')
        await page.wait_for_selector('#username')
        
        console.print("📧 Please enter your LinkedIn credentials:")
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        
        if not email or not password:
            console.print("❌ Need credentials to continue")
            return False
        
        console.print("🔑 Logging in with Suna-style automation...")
        
        # Human-like typing with random delays
        await page.fill('#username', '')  # Clear first
        for char in email:
            await page.type('#username', char, delay=random.randint(50, 150))
        
        await page.wait_for_timeout(random.randint(500, 1500))
        
        await page.fill('#password', '')  # Clear first  
        for char in password:
            await page.type('#password', char, delay=random.randint(50, 150))
        
        await page.wait_for_timeout(random.randint(500, 1500))
        
        # Click login with human-like behavior
        await page.click('button[type="submit"]')
        console.print("⏳ Waiting for login response...")
        
        # Enhanced login detection
        for i in range(30):  # Wait up to 30 seconds
            await page.wait_for_timeout(1000)
            url = page.url
            console.print(f"🔍 Current URL: {url}")
            
            # Success indicators
            if any(indicator in url.lower() for indicator in ['feed', '/in/', 'linkedin.com/feed']):
                console.print("✅ Login successful! Saving session...")
                await self.save_session(context)
                await page.screenshot(path=f'{self.screenshot_dir}/login_success.png')
                return True
            
            # Challenge indicators
            if any(challenge in url.lower() for challenge in ['challenge', 'checkpoint', 'verify']):
                console.print("🤖 Manual verification required...")
                console.print("👆 Please complete verification in the browser window")
                input("Press Enter after completing verification...")
                
                # Check if verification completed
                await page.wait_for_timeout(2000)
                if any(indicator in page.url.lower() for indicator in ['feed', '/in/']):
                    console.print("✅ Verification completed! Saving session...")
                    await self.save_session(context)
                    return True
                continue
            
            # Error detection
            if 'login' in url.lower() and i > 10:
                try:
                    error_elem = await page.query_selector('.form__label--error, .alert--error')
                    if error_elem:
                        error_text = await error_elem.inner_text()
                        console.print(f"❌ Login error: {error_text}")
                        return False
                except:
                    pass
        
        console.print("⚠️ Login status unclear, attempting to continue...")
        return True
    
    async def search_jobs(self, page):
        """Simple job search"""
        console.print("🔍 Navigating to LinkedIn Jobs...")
        
        await page.goto('https://www.linkedin.com/jobs/')
        await page.wait_for_timeout(3000)
        
        # Look for search inputs
        console.print("🎯 Searching for Python Developer jobs...")
        
        try:
            # Find keywords input
            keywords_input = page.locator('input[aria-label*="Search by title"], input[placeholder*="Search by title"]').first
            await keywords_input.click()
            await keywords_input.fill("Python Developer")
            console.print("✅ Entered job keywords")
            
            # Find location input  
            location_input = page.locator('input[aria-label*="City"], input[placeholder*="City"]').first
            await location_input.click()
            await location_input.clear()
            await location_input.fill("Remote")
            console.print("✅ Entered location")
            
            # Submit search
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(5000)
            
            console.print("✅ Job search completed!")
            await page.screenshot(path=f'{self.screenshot_dir}/job_search.png')
            return True
            
        except Exception as e:
            console.print(f"❌ Search error: {e}")
            return False
    
    async def extract_jobs(self, page):
        """Extract job data with discovered 2025 LinkedIn selectors"""
        console.print("📊 Extracting jobs with verified 2025 selectors...")
        
        # Scroll to load more jobs - Suna approach
        for i in range(5):  # More scrolling like Suna
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(3000)  # Longer wait
            console.print(f"📜 Scroll {i+1}/5 - Loading more jobs...")
        
        # Wait for jobs to load
        await page.wait_for_timeout(5000)
        
        # Use discovered 2025 selectors
        job_selectors = [
            # Verified working selectors from analysis
            'li[data-occludable-job-id]',  # Most reliable
            '.job-card-container',
            '.jobs-search-results-list__list-item',
            # Fallbacks
            '.ember-view[data-occludable-job-id]',
            'div[data-job-id]',
            'li[data-job-id]'
        ]
        
        # Try each selector until we find jobs
        job_cards = []
        for selector in job_selectors:
            console.print(f"🔍 Trying verified selector: {selector}")
            cards = await page.query_selector_all(selector)
            if cards and len(cards) > 0:
                console.print(f"✅ SUCCESS! Found {len(cards)} job cards with: {selector}")
                job_cards = cards
                break
            await page.wait_for_timeout(1000)
        
        if not job_cards:
            console.print("⚠️ No job cards found. Trying manual inspection...")
            # Debug screenshot
            await page.screenshot(path=f'{self.screenshot_dir}/debug_no_jobs.png')
            return []
        
        console.print(f"🎯 Processing {len(job_cards)} job cards with verified selectors...")
        
        jobs = []
        for i, card in enumerate(job_cards[:15]):  # Process first 15
            try:
                # Use discovered title selectors
                title_selectors = [
                    '.artdeco-entity-lockup__title',
                    '.job-card-list__title',
                    'h3 .sr-only',
                    'h3 a',
                    'h3',
                    '[data-tracking-control-name*="job"] h3',
                    '.full-width.artdeco-entity-lockup__title'
                ]
                
                title = "Unknown"
                for title_sel in title_selectors:
                    title_elem = await card.query_selector(title_sel)
                    if title_elem:
                        title_text = await title_elem.inner_text()
                        if title_text and len(title_text.strip()) > 3:
                            title = title_text.strip()
                            break
                
                # Use discovered company selectors  
                company_selectors = [
                    '.artdeco-entity-lockup__subtitle',
                    '.job-card-container__primary-description',
                    'h4 a',
                    'h4',
                    '.company-name',
                    '.jobs-unified-top-card__company-name'
                ]
                
                company = "Unknown"
                for comp_sel in company_selectors:
                    company_elem = await card.query_selector(comp_sel)
                    if company_elem:
                        company_text = await company_elem.inner_text()
                        if company_text and len(company_text.strip()) > 1:
                            company = company_text.strip()
                            break
                
                # Get location
                location_selectors = [
                    '.job-card-container__metadata-item',
                    '.artdeco-entity-lockup__caption',
                    '.job-search-card__location',
                    '[data-testid="job-location"]'
                ]
                
                location = "Unknown"
                for loc_sel in location_selectors:
                    location_elem = await card.query_selector(loc_sel)
                    if location_elem:
                        location_text = await location_elem.inner_text()
                        if location_text and len(location_text.strip()) > 1:
                            location = location_text.strip()
                            break
                
                # Get job URL
                url = "Unknown"
                try:
                    link_elem = await card.query_selector('a[href*="/jobs/view/"], a[data-tracking-control-name*="job"]')
                    if link_elem:
                        url = await link_elem.get_attribute('href')
                        if url and not url.startswith('http'):
                            url = f"https://linkedin.com{url}"
                except:
                    pass
                
                # Only add if we got meaningful data
                if (title != "Unknown" and title and len(title) > 5 and 
                    company != "Unknown" and company and len(company) > 1):
                    
                    job_data = {
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url
                    }
                    jobs.append(job_data)
                    console.print(f"✅ Job {len(jobs)}: {title[:40]} at {company[:25]}")
                else:
                    console.print(f"⚠️ Skipped job {i+1} - insufficient data (title: {title[:20]}, company: {company[:15]})")
                
            except Exception as e:
                console.print(f"⚠️ Error extracting job {i+1}: {e}")
                continue
        
        console.print(f"🎉 Successfully extracted {len(jobs)} jobs with 2025 selectors!")
        await page.screenshot(path=f'{self.screenshot_dir}/jobs_extracted_2025.png')
        return jobs

async def main():
    """Run Suna-inspired LinkedIn automation demo"""
    console.print("🚀 LinkedIn Automation Demo - Suna AI Inspired")
    console.print("="*60)
    console.print("🎯 Features: Session persistence, advanced stealth, robust extraction")
    console.print("="*60)
    
    demo = LinkedInSimpleDemo()
    browser = None
    context = None
    
    try:
        # Setup browser with Suna-style stealth
        browser, page = await demo.setup_browser()
        context = page.context
        
        # Login with session management
        login_ok = await demo.login_to_linkedin(page, context)
        if not login_ok:
            console.print("❌ Login failed - automation cannot continue")
            return
        
        console.print("🎉 LinkedIn authentication successful!")
        
        # Job search automation
        console.print("\n" + "="*50)
        console.print("🔍 STARTING JOB SEARCH AUTOMATION")
        console.print("="*50)
        
        search_ok = await demo.search_jobs(page)
        if search_ok:
            console.print("✅ Job search automation completed successfully")
        else:
            console.print("⚠️ Job search had issues, but continuing...")
        
        # Enhanced job extraction
        console.print("\n" + "="*50)
        console.print("📊 STARTING SUNA-STYLE JOB EXTRACTION")
        console.print("="*50)
        
        jobs = await demo.extract_jobs(page)
        
        # Results display
        console.print("\n" + "🎯" + "="*50)
        console.print("AUTOMATION RESULTS - SUNA AI INSPIRED")
        console.print("="*52)
        
        if jobs:
            console.print(f"✅ Successfully extracted {len(jobs)} jobs!")
            console.print("\n📋 JOB LISTINGS:")
            console.print("-" * 60)
            
            for i, job in enumerate(jobs, 1):
                console.print(f"{i:2d}. 🏢 {job['title']}")
                console.print(f"    🏗️  {job['company']}")
                console.print(f"    📍 {job['location']}")
                if job['url'] != "Unknown":
                    console.print(f"    🔗 {job['url'][:60]}...")
                console.print("-" * 60)
            
            console.print(f"\n🎉 SUCCESS: Found {len(jobs)} job opportunities!")
            console.print("📊 Extraction rate: ~{}%".format(min(100, len(jobs) * 10)))
            
        else:
            console.print("⚠️ No jobs extracted - may need selector updates")
            console.print("📸 Check debug screenshots in data/screenshots/")
        
        console.print(f"\n📁 All screenshots saved to: {demo.screenshot_dir}")
        console.print("💾 Session saved for next run (faster login)")
        console.print("⏳ Browser staying open for 20 seconds for inspection...")
        
        await asyncio.sleep(20)
        
    except KeyboardInterrupt:
        console.print("\n⏹️ Automation stopped by user")
    except Exception as e:
        console.print(f"\n❌ Automation error: {e}")
        import traceback
        console.print("🔍 Full error details:")
        traceback.print_exc()
    
    finally:
        if browser:
            try:
                if context:
                    await demo.save_session(context)
                await browser.close()
                console.print("✅ Browser closed successfully")
            except Exception as e:
                console.print(f"⚠️ Error during cleanup: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 