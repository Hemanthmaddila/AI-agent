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
    'create_scraper_manager'
]

def create_scraper_manager(enabled_sources: list = None) -> ScraperManager:
    """
    Factory function to create a ScraperManager with all available scrapers registered.
    
    Args:
        enabled_sources: List of source names to enable. If None, enables all.
                        Options: ['remote.co', 'linkedin', 'indeed']
    
    Returns:
        Configured ScraperManager instance
    """
    manager = ScraperManager()
    
    # Register all available scrapers
    scrapers = {
        'remote.co': RemoteCoScraper(),
        'linkedin': LinkedInScraper(),
        'indeed': IndeedScraper()
    }
    
    # Determine which scrapers to enable
    if enabled_sources is None:
        # Enable Remote.co by default, others require user decision
        enabled_sources = ['remote.co']
    
    # Convert to lowercase for consistent comparison
    enabled_sources = [source.lower() for source in enabled_sources]
    
    # Register scrapers with appropriate enabled status
    for source_name, scraper in scrapers.items():
        is_enabled = source_name in enabled_sources
        manager.register_scraper(scraper, enabled=is_enabled)
    
    return manager

def get_available_scrapers() -> dict:
    """
    Get information about all available scrapers.
    
    Returns:
        Dictionary with scraper information including capabilities and requirements
    """
    return {
        'remote.co': {
            'name': 'Remote.co',
            'class': 'RemoteCoScraper',
            'authentication_required': False,
            'challenges': ['Rate limiting', 'Dynamic selectors'],
            'reliability': 'High',
            'description': 'Specialized remote work job board with good scraping reliability'
        },
        'linkedin': {
            'name': 'LinkedIn',
            'class': 'LinkedInScraper', 
            'authentication_required': True,
            'challenges': ['Login required', 'Strong anti-bot', 'CAPTCHAs'],
            'reliability': 'Medium',
            'description': 'Professional network with extensive job listings but requires authentication'
        },
        'indeed': {
            'name': 'Indeed',
            'class': 'IndeedScraper',
            'authentication_required': False,
            'challenges': ['Dynamic content', 'Anti-scraping', 'Aggregated sources'],
            'reliability': 'Medium',
            'description': 'Large job aggregator with dynamic content and bot detection'
        }
    } 