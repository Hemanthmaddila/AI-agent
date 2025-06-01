#!/usr/bin/env python3
"""
Simple Browser Demo - Test Playwright Setup
Quick test to ensure browser automation is working
"""

import asyncio
from playwright.async_api import async_playwright
from rich.console import Console
from rich.panel import Panel

console = Console()

async def simple_browser_test():
    """Simple test to verify browser automation works"""
    console.print(Panel("🧪 Testing Browser Automation Setup", style="cyan"))
    
    try:
        # Start Playwright
        async with async_playwright() as playwright:
            console.print("✅ Playwright initialized successfully")
            
            # Launch browser
            browser = await playwright.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-default-apps'
                ]
            )
            console.print("✅ Browser launched successfully")
            
            # Create page
            page = await browser.new_page()
            console.print("✅ New page created")
            
            # Navigate to a test site
            console.print("🌐 Navigating to Google...")
            await page.goto('https://www.google.com')
            console.print("✅ Navigation successful")
            
            # Wait a moment
            await page.wait_for_timeout(3000)
            
            # Get page title
            title = await page.title()
            console.print(f"📄 Page title: {title}")
            
            # Take a screenshot
            await page.screenshot(path='data/test_screenshot.png')
            console.print("📸 Screenshot saved to data/test_screenshot.png")
            
            # Keep browser open for 5 seconds
            console.print("⏳ Keeping browser open for 5 seconds...")
            await asyncio.sleep(5)
            
            # Close browser
            await browser.close()
            console.print("✅ Browser closed successfully")
            
            console.print(Panel("🎉 Browser automation test completed successfully!", style="green"))
            
    except Exception as e:
        console.print(f"❌ Error during browser test: {e}")
        console.print("💡 Please ensure you have installed Playwright browsers:")
        console.print("   Run: python -m playwright install")

if __name__ == "__main__":
    asyncio.run(simple_browser_test()) 