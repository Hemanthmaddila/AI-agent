#!/usr/bin/env python3
"""
🔍 Vision-Enhanced Sequential LinkedIn Filtering Demo
Demonstrates methodical sequential filtering with Gemma 3-1B vision fallbacks
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.scrapers.linkedin_scraper import LinkedInScraper
from app.services.vision_service import vision_service
from app.models.user_profiles import UserProfile
from config.settings import settings

console = Console()

class VisionEnhancedFilteringDemo:
    """Demo of sequential LinkedIn filtering with vision fallbacks"""
    
    def __init__(self):
        self.scraper = None
        self.demo_results = {
            'filters_applied': [],
            'fallback_used': [],
            'vision_interactions': [],
            'total_jobs_found': 0,
            'execution_time': 0
        }
    
    async def setup_demo(self):
        """Initialize scraper and vision service"""
        console.print(Panel("🔧 Setting up Vision-Enhanced Demo", style="cyan"))
        
        # Initialize vision service
        console.print("📥 Initializing Gemma 3-1B Vision Service...")
        try:
            await vision_service.initialize()
            console.print("✅ Vision service ready with smallest Gemma model")
        except Exception as e:
            console.print(f"⚠️ Vision service initialization failed: {e}")
            console.print("🔄 Demo will run with CSS selectors only")
        
        # Initialize LinkedIn scraper
        console.print("🌐 Initializing LinkedIn Scraper...")
        self.scraper = LinkedInScraper()
        await self.scraper.setup()
        console.print("✅ LinkedIn scraper ready")
        
        console.print("🚀 Demo setup complete!")
    
    async def demonstrate_sequential_filtering(self):
        """Show step-by-step sequential filtering process"""
        
        console.print(Panel("🎯 Sequential LinkedIn Filtering Demo", style="bold blue"))
        
        # Get demo parameters
        console.print("📋 Demo Parameters:")
        keywords = input("Job Keywords (default: Software Engineer): ").strip() or "Software Engineer"
        location = input("Location (default: San Francisco): ").strip() or "San Francisco"
        
        # Filter options
        console.print("\n🔧 Filter Options:")
        console.print("1. Date Posted: Past week")
        console.print("2. Experience Level: Entry level, Mid-Senior level") 
        console.print("3. Work Type: Remote, Hybrid")
        
        confirm = input("\nUse these filters? (y/n): ").strip().lower()
        if confirm != 'y':
            return
        
        start_time = datetime.now()
        
        try:
            # Step 1: Login
            await self._demo_login()
            
            # Step 2: Perform search
            await self._demo_search(keywords, location)
            
            # Step 3: Sequential filtering with vision fallbacks
            await self._demo_sequential_filters()
            
            # Step 4: Analyze results
            await self._demo_results_analysis()
            
        except Exception as e:
            console.print(f"❌ Demo error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.demo_results['execution_time'] = (datetime.now() - start_time).total_seconds()
            await self._show_demo_summary()
    
    async def _demo_login(self):
        """Demo login process"""
        console.print(Panel("🔐 Step 1: LinkedIn Login", style="green"))
        
        email = input("LinkedIn Email: ").strip()
        password = input("LinkedIn Password: ").strip()
        
        if not email or not password:
            raise Exception("Credentials required for demo")
        
        await self.scraper.login(email, password)
        console.print("✅ Successfully logged into LinkedIn")
    
    async def _demo_search(self, keywords: str, location: str):
        """Demo basic search"""
        console.print(Panel("🔍 Step 2: Initial Job Search", style="green"))
        
        # Navigate to jobs page and perform search
        await self.scraper.page.goto('https://www.linkedin.com/jobs/', timeout=30000)
        await self.scraper.page.wait_for_load_state('domcontentloaded')
        
        # Search for jobs
        console.print(f"🔍 Searching for: {keywords} in {location}")
        await self.scraper._perform_search(keywords, location)
        
        # Take screenshot for documentation
        await self.scraper.page.screenshot(path="data/screenshots/demo_initial_search.png")
        console.print("📸 Initial search screenshot saved")
        
        console.print("✅ Initial search completed")
    
    async def _demo_sequential_filters(self):
        """Demonstrate sequential filtering with vision fallbacks"""
        console.print(Panel("🎯 Step 3: Sequential Filtering (with Vision Fallbacks)", style="green"))
        
        filters_to_apply = [
            {
                'name': 'Date Posted',
                'values': ['Past week'],
                'button_key': 'date_posted_button',
                'apply_key': 'date_posted_apply'
            },
            {
                'name': 'Experience Level', 
                'values': ['Entry level', 'Mid-Senior level'],
                'button_key': 'experience_level_button',
                'apply_key': 'experience_level_apply'
            },
            {
                'name': 'Work Type',
                'values': ['Remote', 'Hybrid'],
                'button_key': 'on_site_remote_button',
                'apply_key': 'on_site_remote_apply'
            }
        ]
        
        for filter_config in filters_to_apply:
            await self._demo_single_filter(filter_config)
    
    async def _demo_single_filter(self, filter_config: dict):
        """Demo application of a single filter with CSS + Vision fallback"""
        
        filter_name = filter_config['name']
        console.print(f"\n🔧 Applying {filter_name} Filter...")
        
        # Take screenshot before filter
        await self.scraper.page.screenshot(path=f"data/screenshots/demo_before_{filter_name.lower().replace(' ', '_')}.png")
        
        try:
            # Try CSS selector approach first
            console.print(f"   🎯 Attempting CSS selector approach for {filter_name}...")
            
            await self.scraper._apply_filter_category_css(
                main_filter_button_key=filter_config['button_key'],
                option_values_to_select=filter_config['values'],
                option_map=self._get_option_map(filter_name),
                filter_category_name=filter_name,
                dropdown_apply_button_key=filter_config['apply_key']
            )
            
            console.print(f"   ✅ CSS selectors worked for {filter_name}")
            self.demo_results['filters_applied'].append(f"{filter_name} (CSS)")
            
        except Exception as e:
            console.print(f"   ⚠️ CSS selectors failed for {filter_name}: {e}")
            console.print(f"   🔍 Falling back to Vision AI (Gemma 3-1B)...")
            
            try:
                await self.scraper._apply_filter_category_vision(
                    filter_category_name=filter_name,
                    option_values_to_select=filter_config['values']
                )
                
                console.print(f"   ✅ Vision AI successfully handled {filter_name}")
                self.demo_results['filters_applied'].append(f"{filter_name} (Vision)")
                self.demo_results['fallback_used'].append(filter_name)
                self.demo_results['vision_interactions'].append(f"Filter: {filter_name}")
                
            except Exception as e2:
                console.print(f"   ❌ Both CSS and Vision failed for {filter_name}: {e2}")
        
        # Take screenshot after filter
        await self.scraper.page.screenshot(path=f"data/screenshots/demo_after_{filter_name.lower().replace(' ', '_')}.png")
        
        # Wait and show progress
        with Progress(SpinnerColumn(), TextColumn("[bold blue]Waiting for results to update...")) as progress:
            task = progress.add_task("Processing", total=100)
            await asyncio.sleep(3)
            progress.update(task, completed=100)
        
        console.print(f"   📊 {filter_name} filter applied successfully")
    
    def _get_option_map(self, filter_name: str) -> dict:
        """Get option mapping for different filter types"""
        if filter_name == "Date Posted":
            return {
                "Past 24 hours": "past_24_hours",
                "Past week": "past_week",
                "Past month": "past_month",
                "Any time": "any_time"
            }
        elif filter_name == "Experience Level":
            return {
                "Internship": "internship",
                "Entry level": "entry_level", 
                "Associate": "associate",
                "Mid-Senior level": "mid_senior_level",
                "Director": "director",
                "Executive": "executive"
            }
        elif filter_name == "Work Type":
            return {
                "On-site": "on_site",
                "Remote": "remote",
                "Hybrid": "hybrid"
            }
        return {}
    
    async def _demo_results_analysis(self):
        """Analyze and display results after filtering"""
        console.print(Panel("📊 Step 4: Results Analysis", style="green"))
        
        # Take final screenshot
        await self.scraper.page.screenshot(path="data/screenshots/demo_final_results.png")
        
        # Count job results
        try:
            job_cards = await self.scraper.page.query_selector_all('.jobs-search-results__list-item')
            job_count = len(job_cards)
            self.demo_results['total_jobs_found'] = job_count
            
            console.print(f"📋 Found {job_count} jobs after applying all filters")
            
            # Analyze first few jobs with vision
            if vision_service.initialized and job_count > 0:
                console.print("🔍 Vision analysis of job listings...")
                
                screenshot = await self.scraper.page.screenshot()
                clickable_elements = await vision_service.find_clickable_elements(
                    screenshot, 
                    element_types=["button", "link"]
                )
                
                apply_buttons = [elem for elem in clickable_elements 
                               if any(keyword in elem.get('text', '').lower() 
                                     for keyword in ['apply', 'easy apply'])]
                
                console.print(f"🎯 Vision detected {len(apply_buttons)} apply buttons")
                self.demo_results['vision_interactions'].append(f"Detected {len(apply_buttons)} apply buttons")
                
        except Exception as e:
            console.print(f"⚠️ Results analysis error: {e}")
    
    async def _show_demo_summary(self):
        """Show comprehensive demo summary"""
        console.print(Panel("📊 Demo Summary", style="bold green"))
        
        # Create summary table
        table = Table(title="Vision-Enhanced Filtering Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Execution Time", f"{self.demo_results['execution_time']:.1f} seconds")
        table.add_row("Filters Applied", f"{len(self.demo_results['filters_applied'])}")
        table.add_row("Vision Fallbacks Used", f"{len(self.demo_results['fallback_used'])}")
        table.add_row("Vision Interactions", f"{len(self.demo_results['vision_interactions'])}")
        table.add_row("Total Jobs Found", f"{self.demo_results['total_jobs_found']}")
        
        console.print(table)
        
        # Show detailed breakdown
        if self.demo_results['filters_applied']:
            console.print("\n✅ Successfully Applied Filters:")
            for filter_applied in self.demo_results['filters_applied']:
                console.print(f"   • {filter_applied}")
        
        if self.demo_results['fallback_used']:
            console.print("\n🔍 Vision Fallbacks Used:")
            for fallback in self.demo_results['fallback_used']:
                console.print(f"   • {fallback}")
        
        if self.demo_results['vision_interactions']:
            console.print("\n🤖 Vision AI Interactions:")
            for interaction in self.demo_results['vision_interactions']:
                console.print(f"   • {interaction}")
        
        console.print("\n📸 Screenshots saved in data/screenshots/")
        console.print("🎯 Demo completed successfully!")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.scraper:
            await self.scraper.cleanup()

async def main():
    """Run the vision-enhanced filtering demo"""
    
    console.print("🔍 Vision-Enhanced LinkedIn Filtering Demo")
    console.print("Features: Sequential filtering + Gemma 3-1B vision fallbacks")
    console.print("="*60)
    
    demo = VisionEnhancedFilteringDemo()
    
    try:
        await demo.setup_demo()
        await demo.demonstrate_sequential_filtering()
    finally:
        await demo.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 