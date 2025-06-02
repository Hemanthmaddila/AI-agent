#!/usr/bin/env python3
"""
Test Visible Browser - Make sure browser shows up visually
Forces browser window to be visible and interactive
"""

import asyncio
from playwright.async_api import async_playwright
from rich.console import Console
from rich.panel import Panel

console = Console()

async def test_visible_browser():
    """Test browser with maximum visibility settings"""
    console.print(Panel("🔍 Testing VISIBLE Browser Setup", style="cyan"))
    
    try:
        async with async_playwright() as playwright:
            # Launch browser with maximum visibility
            browser = await playwright.chromium.launch(
                headless=False,  # Definitely NOT headless
                slow_mo=1000,    # Slow down for visibility
                args=[
                    '--start-maximized',  # Start maximized
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            console.print("✅ VISIBLE Browser launched!")
            
            # Create page
            page = await browser.new_page()
            
            # Set large viewport
            await page.set_viewport_size({"width": 1366, "height": 768})
            
            console.print("🌐 Opening LinkedIn...")
            await page.goto('https://www.linkedin.com')
            
            console.print("⏳ Browser will stay open for 30 seconds - YOU SHOULD SEE IT NOW!")
            console.print("📍 Look for a Chrome browser window that just opened")
            
            # Wait 30 seconds so you can see it
            for i in range(30, 0, -1):
                console.print(f"⏰ Browser visible for {i} more seconds...")
                await asyncio.sleep(1)
            
            console.print("🔒 Closing browser...")
            await browser.close()
            
            console.print(Panel("✅ If you saw the browser, everything is working!", style="green"))
            
    except Exception as e:
        console.print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_visible_browser()) 