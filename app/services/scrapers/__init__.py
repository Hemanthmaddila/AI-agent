# Multi-Site Job Discovery Scrapers Package
"""
Phase 4.1: Multi-Site Job Discovery Architecture

This package contains specialized scrapers for different job platforms:
- base_scraper.py: Abstract base class with common functionality
- remote_co_scraper.py: Remote.co scraper (refactored from original)
- linkedin_scraper.py: LinkedIn Jobs scraper with authentication handling
- indeed_scraper.py: Indeed scraper with dynamic content support
- scraper_manager.py: Orchestrates multiple scrapers and handles deduplication

Each scraper implements the JobScraper interface for consistent behavior.
"""

from .base_scraper import JobScraper, ScraperConfig, ScraperResult
from .scraper_manager import ScraperManager, MultiSiteSearchResult
from .remote_co_scraper import RemoteCoScraper
from .linkedin_scraper import LinkedInScraper, LinkedInScraperConfig
from .indeed_scraper import IndeedScraper
from .stackoverflow_scraper import StackOverflowJobsScraper

__all__ = [
    'JobScraper', 
    'ScraperConfig', 
    'ScraperResult',
    'ScraperManager', 
    'MultiSiteSearchResult',
    'RemoteCoScraper',
    'LinkedInScraper',
    'LinkedInScraperConfig',
    'IndeedScraper',
    'StackOverflowJobsScraper',
    'create_scraper_manager',
    'get_available_scrapers'
]

def create_scraper_manager(enabled_sources=None, configs=None):
    """Factory function to create a configured ScraperManager"""
    if enabled_sources is None:
        enabled_sources = ['remote.co', 'indeed', 'stackoverflow']  # Default safe sources
    
    if configs is None:
        configs = {
            'remote.co': ScraperConfig(),
            'linkedin': ScraperConfig(min_delay=3, max_delay=7),
            'indeed': ScraperConfig(min_delay=2, max_delay=5),
            'stackoverflow': ScraperConfig(min_delay=1, max_delay=3)
        }
    
    # Create scraper instances
    scrapers = {}
    
    for source in enabled_sources:
        try:
            config = configs.get(source, ScraperConfig())
            
            if source == 'remote.co':
                scrapers[source] = RemoteCoScraper(config)
            elif source == 'linkedin':
                scrapers[source] = LinkedInScraper(config)
            elif source == 'indeed':
                scrapers[source] = IndeedScraper(config)
            elif source == 'stackoverflow':
                scrapers[source] = StackOverflowJobsScraper(config)
            else:
                print(f"Warning: Unknown scraper source '{source}' skipped")
                
        except Exception as e:
            print(f"Error creating scraper for {source}: {e}")
    
    return ScraperManager(scrapers)

def get_available_scrapers():
    """Get information about all available job scrapers"""
    return {
        'remote.co': {
            'name': 'Remote.co',
            'description': 'Premium remote job board with curated positions',
            'authentication_required': False,
            'reliability': 'High'
        },
        'linkedin': {
            'name': 'LinkedIn Jobs',
            'description': 'Professional network with comprehensive job listings',
            'authentication_required': True,
            'reliability': 'High'
        },
        'indeed': {
            'name': 'Indeed',
            'description': 'World\'s largest job site with millions of listings',
            'authentication_required': False,
            'reliability': 'Medium'
        },
        'stackoverflow': {
            'name': 'Stack Overflow Jobs',
            'description': 'Developer-focused job board with high-quality tech positions',
            'authentication_required': False,
            'reliability': 'High'
        }
    } 