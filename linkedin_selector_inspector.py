#!/usr/bin/env python3
"""
LinkedIn Selector Inspector - Find Current Job Card Selectors
Analyzes LinkedIn Jobs page to find working selectors for 2025
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console

console = Console()

async def inspect_linkedin_selectors():
    """Inspect LinkedIn page to find current job selectors"""
    console.print("🔍 LinkedIn Selector Inspector - Finding 2025 Selectors")
    console.print("="*60)
    
    playwright = await async_playwright().start()
    
    # Launch browser (same config as main demo)
    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-extensions'
        ]
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    
    page = await context.new_page()
    
    try:
        # Load existing session if available
        session_file = "data/linkedin_session.json"
        if Path(session_file).exists():
            console.print("📂 Loading existing LinkedIn session...")
            with open(session_file, 'r') as f:
                state = json.load(f)
            await context.add_cookies(state.get('cookies', []))
        
        # Navigate to LinkedIn Jobs
        console.print("🌐 Navigating to LinkedIn Jobs...")
        await page.goto('https://www.linkedin.com/jobs/search/?keywords=Python%20Developer&location=Remote')
        await page.wait_for_timeout(5000)
        
        # Scroll to load jobs
        console.print("📜 Scrolling to load job listings...")
        for i in range(3):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)
        
        # Analyze page structure
        console.print("🔍 Analyzing page structure...")
        
        # Get all elements that might be job cards
        potential_selectors = [
            'li', 'article', 'div[data-job-id]', 'div[data-occludable-job-id]',
            '[class*="job"]', '[class*="card"]', '[data-testid*="job"]'
        ]
        
        job_elements = []
        
        for selector in potential_selectors:
            elements = await page.query_selector_all(selector)
            for element in elements:
                try:
                    # Get element info
                    tag_name = await element.evaluate('el => el.tagName')
                    class_name = await element.get_attribute('class') or ''
                    data_attrs = await element.evaluate('''el => {
                        const attrs = {};
                        for (let attr of el.attributes) {
                            if (attr.name.startsWith('data-')) {
                                attrs[attr.name] = attr.value;
                            }
                        }
                        return attrs;
                    }''')
                    
                    # Check if it contains job-related content
                    text_content = await element.inner_text()
                    
                    if (('job' in class_name.lower() or 
                         any('job' in str(v).lower() for v in data_attrs.values()) or
                         any(keyword in text_content.lower() for keyword in ['engineer', 'developer', 'software', 'python'])) 
                        and len(text_content.strip()) > 50):
                        
                        # Look for title and company within this element
                        title_elem = await element.query_selector('h3, h2, h1, [class*="title"], [class*="job-title"]')
                        company_elem = await element.query_selector('[class*="company"], h4, [class*="subtitle"]')
                        
                        if title_elem and company_elem:
                            title = await title_elem.inner_text()
                            company = await company_elem.inner_text()
                            
                            job_elements.append({
                                'selector': f'{tag_name}.{class_name.split()[0] if class_name else "no-class"}',
                                'full_class': class_name,
                                'data_attrs': data_attrs,
                                'title': title.strip()[:50],
                                'company': company.strip()[:30],
                                'title_selector': await title_elem.evaluate('el => el.className'),
                                'company_selector': await company_elem.evaluate('el => el.className')
                            })
                            
                except Exception as e:
                    continue
        
        # Remove duplicates and analyze
        unique_jobs = []
        seen_titles = set()
        
        for job in job_elements:
            if job['title'] not in seen_titles and len(job['title']) > 10:
                seen_titles.add(job['title'])
                unique_jobs.append(job)
        
        # Display findings
        console.print(f"\n🎯 Found {len(unique_jobs)} unique job elements!")
        console.print("\n📋 JOB CARD ANALYSIS:")
        console.print("-" * 80)
        
        for i, job in enumerate(unique_jobs[:10], 1):
            console.print(f"{i:2d}. 🏢 {job['title']}")
            console.print(f"    🏗️  {job['company']}")
            console.print(f"    🔍 Card class: {job['full_class'][:60]}")
            console.print(f"    📝 Title class: {job['title_selector'][:50]}")
            console.print(f"    🏪 Company class: {job['company_selector'][:50]}")
            if job['data_attrs']:
                console.print(f"    📊 Data attrs: {list(job['data_attrs'].keys())}")
            console.print("-" * 80)
        
        # Generate recommended selectors
        if unique_jobs:
            console.print("\n🔧 RECOMMENDED SELECTORS FOR 2025:")
            console.print("="*50)
            
            # Analyze most common patterns
            common_classes = {}
            title_classes = {}
            company_classes = {}
            
            for job in unique_jobs:
                if job['full_class']:
                    main_class = job['full_class'].split()[0]
                    common_classes[main_class] = common_classes.get(main_class, 0) + 1
                
                if job['title_selector']:
                    title_classes[job['title_selector']] = title_classes.get(job['title_selector'], 0) + 1
                
                if job['company_selector']:
                    company_classes[job['company_selector']] = company_classes.get(job['company_selector'], 0) + 1
            
            # Get top selectors
            top_card = max(common_classes.items(), key=lambda x: x[1]) if common_classes else None
            top_title = max(title_classes.items(), key=lambda x: x[1]) if title_classes else None
            top_company = max(company_classes.items(), key=lambda x: x[1]) if company_classes else None
            
            if top_card:
                console.print(f"🎯 Job Card Selector: '.{top_card[0]}' (found {top_card[1]} times)")
            if top_title:
                console.print(f"📝 Job Title Selector: '.{top_title[0]}' (found {top_title[1]} times)")
            if top_company:
                console.print(f"🏪 Company Selector: '.{top_company[0]}' (found {top_company[1]} times)")
            
            # Save selectors to file
            selector_data = {
                'job_cards': [f'.{cls}' for cls, count in sorted(common_classes.items(), key=lambda x: x[1], reverse=True)[:5]],
                'job_titles': [f'.{cls}' for cls, count in sorted(title_classes.items(), key=lambda x: x[1], reverse=True)[:5]],
                'job_companies': [f'.{cls}' for cls, count in sorted(company_classes.items(), key=lambda x: x[1], reverse=True)[:5]],
                'analysis_date': '2025-01-27'
            }
            
            with open('data/linkedin_selectors_2025.json', 'w') as f:
                json.dump(selector_data, f, indent=2)
            
            console.print("\n💾 Selectors saved to: data/linkedin_selectors_2025.json")
        
        console.print("\n📸 Taking final screenshot...")
        await page.screenshot(path='data/screenshots/selector_analysis.png', full_page=True)
        
        console.print("⏳ Browser staying open for manual inspection...")
        await asyncio.sleep(30)
        
    except Exception as e:
        console.print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser.close()
        console.print("✅ Analysis complete!")

if __name__ == "__main__":
    asyncio.run(inspect_linkedin_selectors()) 