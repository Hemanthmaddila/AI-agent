#!/usr/bin/env python3
"""
Debug script to inspect Wellfound page structure
"""
import asyncio
import logging
from playwright.async_api import async_playwright

async def debug_wellfound_page():
    """Debug Wellfound page structure to understand data extraction approach"""
    
    print("🔍 Debugging Wellfound Page Structure")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Run visible for debugging
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        
        # Navigate to Wellfound jobs search
        search_url = "https://wellfound.com/jobs?q=python+developer"
        print(f"📍 Navigating to: {search_url}")
        
        try:
            await page.goto(search_url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(5)  # Extra wait for dynamic content
            
            print(f"✅ Page loaded: {page.url}")
            print(f"📄 Page title: {await page.title()}")
            
            # Check for __NEXT_DATA__
            print("\n🔍 Checking for __NEXT_DATA__ script...")
            next_data_script = await page.query_selector("script#__NEXT_DATA__")
            if next_data_script:
                print("✅ Found __NEXT_DATA__ script")
                json_content = await next_data_script.inner_html()
                print(f"📊 JSON length: {len(json_content)} characters")
                print(f"📝 First 200 chars: {json_content[:200]}...")
            else:
                print("❌ No __NEXT_DATA__ script found")
            
            # Check for other script tags that might contain data
            print("\n🔍 Checking for other data-containing scripts...")
            all_scripts = await page.query_selector_all("script")
            print(f"📊 Total script tags: {len(all_scripts)}")
            
            data_scripts = []
            for i, script in enumerate(all_scripts):
                script_id = await script.get_attribute("id")
                script_type = await script.get_attribute("type")
                script_content = await script.inner_html()
                
                if script_content and len(script_content) > 100:
                    # Look for JSON-like content
                    if any(keyword in script_content for keyword in ['{"', 'window.', '__INITIAL_STATE__', 'apolloState', 'jobs']):
                        data_scripts.append({
                            'index': i,
                            'id': script_id,
                            'type': script_type,
                            'length': len(script_content),
                            'preview': script_content[:100].replace('\n', ' ')
                        })
            
            print(f"📋 Found {len(data_scripts)} potentially data-containing scripts:")
            for script_info in data_scripts[:5]:  # Show first 5
                print(f"  Script {script_info['index']}: ID='{script_info['id']}', Type='{script_info['type']}', Length={script_info['length']}")
                print(f"    Preview: {script_info['preview']}...")
                print()
            
            # Check for job listing elements in the DOM
            print("\n🔍 Checking for job listing elements...")
            job_selectors = [
                '[data-test="StartupResult"]',
                '[data-testid="job-card"]',
                '.job-listing',
                '.startup-result',
                '[class*="job"]',
                '[class*="listing"]',
                '[class*="card"]'
            ]
            
            for selector in job_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with selector: {selector}")
                    
                    # Get details of first element
                    if elements:
                        first_element = elements[0]
                        element_text = await first_element.inner_text()
                        element_html = await first_element.inner_html()
                        print(f"   First element text (first 100 chars): {element_text[:100]}...")
                        print(f"   HTML length: {len(element_html)} characters")
                        break
                else:
                    print(f"❌ No elements found for: {selector}")
            
            # Check page source for patterns
            print("\n🔍 Analyzing page source patterns...")
            page_content = await page.content()
            
            patterns_to_check = [
                'window.__INITIAL_STATE__',
                'window.__APOLLO_STATE__',
                'window.INITIAL_PROPS',
                '"jobs"',
                '"startups"',
                '"listings"',
                'apolloState',
                'graphql'
            ]
            
            found_patterns = []
            for pattern in patterns_to_check:
                if pattern in page_content:
                    found_patterns.append(pattern)
            
            print(f"📋 Found patterns: {found_patterns}")
            
            # Wait for user to inspect manually
            print("\n⏸️  Browser will stay open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"❌ Error during debugging: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_wellfound_page()) 