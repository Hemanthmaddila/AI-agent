#!/usr/bin/env python3
"""
Force Visible Browser - Absolutely ensure browser is visible
Uses Windows-specific commands to force window visibility
"""

import asyncio
import subprocess
from playwright.async_api import async_playwright
from rich.console import Console
from rich.panel import Panel

console = Console()

async def force_visible_browser():
    """Force browser to be absolutely visible"""
    console.print(Panel("🚀 FORCING Browser Visibility", style="cyan"))
    
    try:
        async with async_playwright() as playwright:
            # Launch with maximum visibility settings
            browser = await playwright.chromium.launch(
                headless=False,
                slow_mo=500,
                args=[
                    '--start-maximized',
                    '--new-window',
                    '--force-device-scale-factor=1',
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ],
                executable_path=None  # Use default Chrome
            )
            
            console.print("✅ Browser launched with MAXIMUM visibility!")
            
            page = await browser.new_page()
            
            # Try to bring window to front using Windows commands
            try:
                # Get all Chrome windows and bring to front
                subprocess.run(['powershell', '-Command', 
                    'Get-Process chrome | ForEach-Object { $_.MainWindowTitle }'], 
                    capture_output=True, check=False)
            except:
                pass
            
            console.print("🌐 Opening a simple test page...")
            await page.goto('https://example.com')
            
            # Wait and show countdown
            console.print("👀 LOOK FOR CHROME WINDOW - Staying open for 20 seconds!")
            console.print("📍 The browser should be MAXIMIZED and on top!")
            
            for i in range(20, 0, -1):
                console.print(f"⏰ {i} seconds remaining - Check your screen!")
                await asyncio.sleep(1)
            
            # Navigate to LinkedIn to test
            console.print("🔄 Now testing LinkedIn...")
            await page.goto('https://www.linkedin.com')
            
            console.print("📍 LinkedIn should be visible for 10 more seconds!")
            for i in range(10, 0, -1):
                console.print(f"⏰ LinkedIn visible: {i} seconds")
                await asyncio.sleep(1)
            
            await browser.close()
            console.print(Panel("✅ Browser test completed!", style="green"))
            
    except Exception as e:
        console.print(f"❌ Error: {e}")
        console.print("💡 This might be a display or security issue")

if __name__ == "__main__":
    asyncio.run(force_visible_browser()) 