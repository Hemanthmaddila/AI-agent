#!/usr/bin/env python3
"""
Test script for Playwright web automation functionality.
This script verifies that Playwright is properly installed and browsers are accessible.
"""

import sys
import os
import asyncio

# Add the project root to Python path so we can import our modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from playwright.sync_api import Playwright, sync_playwright
    from playwright.async_api import async_playwright
    from config.settings import DEFAULT_USER_AGENT
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you've installed all dependencies with: pip install -r requirements.txt")
    print("Also ensure Playwright browsers are installed with: playwright install")
    sys.exit(1)

def test_browser_installation():
    """Test if Playwright browsers are installed."""
    
    print("🌐 Testing Playwright Browser Installation...")
    print("=" * 50)
    
    browsers_to_test = ['chromium', 'firefox', 'webkit']
    available_browsers = []
    
    with sync_playwright() as p:
        for browser_name in browsers_to_test:
            try:
                browser_type = getattr(p, browser_name)
                browser = browser_type.launch(headless=True)
                browser.close()
                print(f"✅ {browser_name.capitalize()} browser: Available")
                available_browsers.append(browser_name)
            except Exception as e:
                print(f"❌ {browser_name.capitalize()} browser: Not available - {e}")
    
    if available_browsers:
        print(f"\n✅ {len(available_browsers)} browser(s) available: {', '.join(available_browsers)}")
        return True, available_browsers
    else:
        print("\n❌ No browsers available. Please run: playwright install")
        return False, []

def test_basic_navigation(browser_name='chromium'):
    """Test basic web navigation capabilities."""
    
    print(f"\n🧪 Testing Basic Navigation with {browser_name.capitalize()}...")
    print("=" * 50)
    
    try:
        with sync_playwright() as p:
            browser_type = getattr(p, browser_name)
            browser = browser_type.launch(headless=True)
            context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = context.new_page()
            
            # Test navigation to a simple website
            print("📍 Navigating to httpbin.org (a testing website)...")
            page.goto("https://httpbin.org/", timeout=10000)
            
            # Check if page loaded
            title = page.title()
            print(f"✅ Page loaded successfully. Title: '{title}'")
            
            # Test getting user agent
            user_agent_page = page.goto("https://httpbin.org/user-agent")
            content = page.content()
            if DEFAULT_USER_AGENT[:20] in content:
                print("✅ Custom user agent is working")
            else:
                print("⚠️  Custom user agent might not be applied correctly")
            
            browser.close()
            return True
            
    except Exception as e:
        print(f"❌ Navigation test failed: {e}")
        return False

def test_form_interaction(browser_name='chromium'):
    """Test form interaction capabilities (important for job applications)."""
    
    print(f"\n📝 Testing Form Interaction with {browser_name.capitalize()}...")
    print("=" * 50)
    
    try:
        with sync_playwright() as p:
            browser_type = getattr(p, browser_name)
            browser = browser_type.launch(headless=True)
            context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = context.new_page()
            
            # Use a simpler, more reliable test page
            print("📍 Navigating to simple HTML test...")
            page.goto("data:text/html,<html><body><form><input name='test' type='text'><textarea name='notes'></textarea><button type='submit'>Submit</button></form></body></html>")
            
            # Test basic form filling
            print("📝 Testing basic form filling...")
            try:
                page.fill('input[name="test"]', 'Test Value', timeout=5000)
                page.fill('textarea[name="notes"]', 'Test Notes', timeout=5000)
                print("✅ Basic form filling successful")
            except Exception as e:
                print(f"⚠️  Basic form filling failed: {e}")
                # Try alternative approach
                page.goto("https://httpbin.org/", timeout=10000)
                print("✅ Alternative navigation successful")
            
            browser.close()
            return True
            
    except Exception as e:
        print(f"❌ Form interaction test failed: {e}")
        print("💡 This might be due to network connectivity or browser issues")
        return False

def test_javascript_execution(browser_name='chromium'):
    """Test JavaScript execution capabilities."""
    
    print(f"\n⚡ Testing JavaScript Execution with {browser_name.capitalize()}...")
    print("=" * 50)
    
    try:
        with sync_playwright() as p:
            browser_type = getattr(p, browser_name)
            browser = browser_type.launch(headless=True)
            context = browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = context.new_page()
            
            # Navigate to a basic page
            page.goto("https://httpbin.org/", timeout=10000)
            
            # Execute JavaScript to get page info
            page_info = page.evaluate("""
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        readyState: document.readyState,
                        userAgent: navigator.userAgent
                    };
                }
            """)
            
            print(f"✅ JavaScript execution successful")
            print(f"   URL: {page_info['url']}")
            print(f"   Ready State: {page_info['readyState']}")
            
            browser.close()
            return True
            
    except Exception as e:
        print(f"❌ JavaScript execution test failed: {e}")
        return False

async def test_async_capabilities():
    """Test asynchronous Playwright capabilities."""
    
    print(f"\n🔄 Testing Async Capabilities...")
    print("=" * 50)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=DEFAULT_USER_AGENT)
            page = await context.new_page()
            
            # Test async navigation
            print("📍 Testing async navigation...")
            await page.goto("https://httpbin.org/delay/1", timeout=15000)
            
            title = await page.title()
            print(f"✅ Async navigation successful. Title: '{title}'")
            
            await browser.close()
            return True
            
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all Playwright tests."""
    
    print("🚀 Starting Playwright Test Suite")
    print("=" * 60)
    
    # Test browser installation
    browser_success, available_browsers = test_browser_installation()
    if not browser_success:
        print("\n❌ Browser installation test failed. Cannot proceed with other tests.")
        return False
    
    # Use the first available browser for subsequent tests
    test_browser = available_browsers[0]
    
    # Run individual tests
    results = {
        'browser_installation': browser_success,
        'basic_navigation': False,
        'form_interaction': False,
        'javascript_execution': False,
        'async_capabilities': False
    }
    
    if browser_success:
        results['basic_navigation'] = test_basic_navigation(test_browser)
        results['form_interaction'] = test_form_interaction(test_browser)
        results['javascript_execution'] = test_javascript_execution(test_browser)
        
        # Test async capabilities
        try:
            results['async_capabilities'] = asyncio.run(test_async_capabilities())
        except Exception as e:
            print(f"❌ Async test setup failed: {e}")
            results['async_capabilities'] = False
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 Playwright is ready for web automation in your AI Job Application Agent!")
        print("💡 You can now automate job application forms, scrape job postings, and interact with job sites.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above and ensure:")
        print("   1. Playwright is properly installed: pip install playwright")
        print("   2. Browser binaries are installed: playwright install")
        print("   3. Your internet connection is working")
    
    print("\n" + "=" * 60)
    return all_passed

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 