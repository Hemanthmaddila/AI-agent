#!/usr/bin/env python3
"""
Browser Interface Launcher - Start the Suna-inspired browser automation interface
Run this to see your AI agent in action in real-time through a web browser
"""
import asyncio
import logging
import time
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.browser_automation_service import browser_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data/logs/browser_interface.log')
    ]
)

logger = logging.getLogger(__name__)

def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                 🤖 AI Job Agent - Browser Interface               ║
    ║                  Suna-Inspired Real-Time Automation              ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║                                                                  ║
    ║  🌐 Browser Interface: http://localhost:8080                     ║
    ║  📊 Real-time Progress: Live task tracking                       ║
    ║  📷 Visual Feedback: Screenshots & browser state                 ║
    ║  🔄 WebSocket Updates: Real-time browser automation              ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)

async def demo_job_search():
    """Demo function to show browser automation in action"""
    logger.info("🎯 Starting demo job search to showcase browser automation")
    
    try:
        # Initialize browser
        await browser_service.start_browser()
        
        # Create demo task
        task_id = await browser_service.create_task(
            "Demo: Python Developer Job Search",
            [
                "Initialize browser",
                "Navigate to job site", 
                "Search for Python jobs",
                "Extract job listings",
                "Process results"
            ]
        )
        
        # Simulate job search workflow
        await browser_service.update_task_progress(task_id, "Starting browser automation demo", 10)
        await asyncio.sleep(2)
        
        # Navigate to a job site
        await browser_service.navigate_to("https://stackoverflow.com/jobs", task_id)
        await asyncio.sleep(3)
        
        await browser_service.update_task_progress(task_id, "Searching for Python developer positions", 50)
        await asyncio.sleep(2)
        
        # Simulate search and data extraction
        await browser_service.update_task_progress(task_id, "Extracting job data from page", 75)
        await asyncio.sleep(3)
        
        await browser_service.update_task_progress(task_id, "Demo completed successfully! 🎉", 100)
        
        logger.info("✅ Demo job search completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        if task_id:
            await browser_service.update_task_progress(task_id, f"Demo failed: {str(e)}", error=str(e))

async def start_with_demo():
    """Start browser service with automatic demo"""
    print_banner()
    
    logger.info("🚀 Starting Suna-inspired browser automation service...")
    
    # Create directories
    Path("data/logs").mkdir(parents=True, exist_ok=True)
    Path("data/screenshots").mkdir(parents=True, exist_ok=True)
    
    # Start demo in background after a delay
    async def delayed_demo():
        await asyncio.sleep(5)  # Wait for server to start
        await demo_job_search()
    
    # Schedule demo
    asyncio.create_task(delayed_demo())
    
    # Start the server (this blocks)
    logger.info("🌐 Browser interface starting at http://localhost:8080")
    print("\n💡 Open your browser and go to: http://localhost:8080")
    print("   You'll see live browser automation with visual feedback!")
    print("\n🔄 Press Ctrl+C to stop the service\n")
    
    try:
        browser_service.start_server(host="localhost", port=8080)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down browser interface...")
        await browser_service.close()
    except Exception as e:
        logger.error(f"❌ Server error: {e}")

def main():
    """Main entry point"""
    try:
        # Check if FastAPI and other dependencies are available
        try:
            import fastapi
            import uvicorn
            import websockets
        except ImportError as e:
            print(f"❌ Missing dependency: {e}")
            print("\n📦 Please install additional dependencies:")
            print("   pip install fastapi uvicorn websockets")
            return
        
        # Run the async startup
        asyncio.run(start_with_demo())
        
    except KeyboardInterrupt:
        print("\n🛑 Browser interface stopped by user")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        print(f"\n❌ Failed to start browser interface: {e}")

if __name__ == "__main__":
    main() 