#!/usr/bin/env python3
"""
Advanced debug script for Wellfound - captures network requests and analyzes page structure
"""
import asyncio
import json
import logging
from playwright.async_api import async_playwright

async def debug_wellfound_advanced():
    """Advanced debugging of Wellfound with network monitoring"""
    
    print("🔍 Advanced Wellfound Debugging")
    print("=" * 50)
    
    # Store network requests
    api_requests = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        
        # Monitor network requests
        def handle_request(request):
            if any(keyword in request.url for keyword in ['api', 'graphql', 'jobs', 'search']):
                api_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'post_data': request.post_data
                })
                print(f"📡 API Request: {request.method} {request.url}")
        
        def handle_response(response):
            if any(keyword in response.url for keyword in ['api', 'graphql', 'jobs', 'search']):
                print(f"📥 API Response: {response.status} {response.url}")
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        # Navigate to Wellfound
        search_url = "https://wellfound.com/jobs?q=python+developer"
        print(f"📍 Navigating to: {search_url}")
        
        try:
            await page.goto(search_url, timeout=30000, wait_until="networkidle")
            print(f"✅ Page loaded: {page.url}")
            
            # Wait for dynamic content
            print("⏳ Waiting for dynamic content to load...")
            await asyncio.sleep(10)
            
            # Check if we were redirected or blocked
            current_url = page.url
            if "wellfound.com/jobs" not in current_url:
                print(f"⚠️  Redirected to: {current_url}")
                
                # Check for common blocking patterns
                page_content = await page.content()
                if any(pattern in page_content.lower() for pattern in ['blocked', 'captcha', 'robot', 'access denied']):
                    print("🚫 Appears to be blocked or requires verification")
                    
            # Get page title and content info
            title = await page.title()
            print(f"📄 Page title: {title}")
            
            # Check for job-related content in the page
            page_text = await page.inner_text('body')
            job_keywords = ['python', 'developer', 'engineer', 'software', 'startup', 'company']
            found_keywords = [kw for kw in job_keywords if kw.lower() in page_text.lower()]
            print(f"🔍 Found job-related keywords: {found_keywords}")
            
            # Look for any elements that might contain job data
            print("\n🔍 Searching for job-related elements...")
            
            # Try various selectors
            selectors_to_try = [
                'div[class*="job"]',
                'div[class*="listing"]', 
                'div[class*="card"]',
                'div[class*="result"]',
                'div[class*="startup"]',
                'article',
                '[role="listitem"]',
                'li',
                'a[href*="/l/"]',  # Wellfound job links often use /l/ pattern
                'a[href*="jobs"]'
            ]
            
            for selector in selectors_to_try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"✅ Found {len(elements)} elements with selector: {selector}")
                    
                    # Analyze first few elements
                    for i, element in enumerate(elements[:3]):
                        try:
                            text = await element.inner_text()
                            if text and len(text.strip()) > 10:
                                print(f"   Element {i+1} text: {text[:100]}...")
                                
                                # Check if it looks like a job posting
                                if any(word in text.lower() for word in ['python', 'developer', 'engineer', 'remote', 'salary']):
                                    print(f"   ⭐ This looks like a job posting!")
                                    
                                    # Get more details
                                    html = await element.inner_html()
                                    print(f"   HTML length: {len(html)} chars")
                                    
                                    # Check for links
                                    links = await element.query_selector_all('a')
                                    if links:
                                        for link in links[:2]:
                                            href = await link.get_attribute('href')
                                            if href:
                                                print(f"   Link: {href}")
                        except Exception as e:
                            print(f"   Error analyzing element {i+1}: {e}")
                    break
            
            # Check for any forms or search inputs
            print("\n🔍 Checking for search functionality...")
            search_inputs = await page.query_selector_all('input[type="search"], input[placeholder*="search"], input[name*="search"]')
            if search_inputs:
                print(f"✅ Found {len(search_inputs)} search inputs")
            else:
                print("❌ No search inputs found")
            
            # Summary of network requests
            print(f"\n📊 Network Summary:")
            print(f"   Total API requests captured: {len(api_requests)}")
            
            if api_requests:
                print("   API Endpoints found:")
                for req in api_requests[:5]:  # Show first 5
                    print(f"     {req['method']} {req['url']}")
            
            # Keep browser open for manual inspection
            print(f"\n⏸️  Browser staying open for 60 seconds for manual inspection...")
            print(f"   Current URL: {page.url}")
            print(f"   You can manually inspect the page structure")
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"❌ Error during debugging: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()
    
    # Save API requests for analysis
    if api_requests:
        with open('wellfound_api_requests.json', 'w') as f:
            json.dump(api_requests, f, indent=2)
        print(f"💾 Saved {len(api_requests)} API requests to wellfound_api_requests.json")

if __name__ == "__main__":
    asyncio.run(debug_wellfound_advanced()) 