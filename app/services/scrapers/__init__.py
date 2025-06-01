# Multi-Site Job Discovery Scrapers Package
"""
Phase 4.1: Multi-Site Job Discovery Architecture

This package contains specialized scrapers for different job platforms:
- base_scraper.py: Abstract base class with common functionality
- remote_co_scraper.py: Remote.co scraper (refactored from original)
- linkedin_scraper.py: LinkedIn Jobs scraper with authentication handling
- indeed_scraper.py: Indeed scraper with dynamic content support
- stackoverflow_scraper.py: Stack Overflow Jobs scraper for developer positions
- wellfound_scraper.py: Wellfound (AngelList) scraper for startup jobs
- scraper_manager.py: Orchestrates multiple scrapers and handles deduplication

Each scraper implements the JobScraper interface for consistent behavior.
"""

from .base_scraper import JobScraper, ScraperConfig, ScraperResult
from .scraper_manager import ScraperManager, MultiSiteSearchResult
from .remote_co_scraper import RemoteCoScraper
from .linkedin_scraper import LinkedInScraper
from .indeed_scraper import IndeedScraper
from .stackoverflow_scraper import StackOverflowJobsScraper
from .wellfound_scraper import WellfoundScraper

__all__ = [
    'JobScraper', 
    'ScraperConfig', 
    'ScraperResult',
    'ScraperManager', 
    'MultiSiteSearchResult',
    'RemoteCoScraper',
    'LinkedInScraper',
    'IndeedScraper',
    'StackOverflowJobsScraper',
    'WellfoundScraper',
    'create_scraper_manager',
    'get_available_scrapers'
]

def create_scraper_manager(enabled_sources=None, configs=None):
    """Factory function to create a configured ScraperManager"""
    if enabled_sources is None:
        enabled_sources = ['remote.co', 'indeed', 'stackoverflow', 'wellfound']  # Default safe sources
    
    if configs is None:
        configs = {
            'remote.co': ScraperConfig(),
            'linkedin': ScraperConfig(delay_range=(3, 7)),
            'indeed': ScraperConfig(delay_range=(2, 5)),
            'stackoverflow': ScraperConfig(delay_range=(1, 3)),
            'wellfound': ScraperConfig(delay_range=(2, 5))
        }
    
    # Create scraper manager
    manager = ScraperManager()
    
    # Create and register scraper instances with explicit source names
    for source in enabled_sources:
        try:
            config = configs.get(source, ScraperConfig())
            
            if source == 'remote.co':
                scraper = RemoteCoScraper(config)
                # Override the registration to use our expected source name
                manager.scrapers['remote.co'] = scraper
                manager.enabled_sources.add('remote.co')
            elif source == 'linkedin':
                scraper = LinkedInScraper(config)
                manager.scrapers['linkedin'] = scraper
                manager.enabled_sources.add('linkedin')
            elif source == 'indeed':
                scraper = IndeedScraper(config)
                manager.scrapers['indeed'] = scraper
                manager.enabled_sources.add('indeed')
            elif source == 'stackoverflow':
                scraper = StackOverflowJobsScraper(config)
                manager.scrapers['stackoverflow'] = scraper
                manager.enabled_sources.add('stackoverflow')
            elif source == 'wellfound':
                scraper = WellfoundScraper()
                manager.scrapers['wellfound'] = scraper
                manager.enabled_sources.add('wellfound')
            else:
                print(f"Warning: Unknown scraper source '{source}' skipped")
                
        except Exception as e:
            print(f"Error creating scraper for {source}: {e}")
    
    return manager

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
        },
        'wellfound': {
            'name': 'Wellfound',
            'description': 'Startup and tech jobs with equity, funding, and company data',
            'authentication_required': False,
            'reliability': 'High'
        }
    } 