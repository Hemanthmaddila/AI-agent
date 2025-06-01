"""
Enhanced Configuration Settings for Multi-Platform Job Automation
"""
import os
from typing import List, Dict, Any

class EnhancedSettings:
    """Enhanced settings for multi-platform job automation"""
    
    # AI Service Configuration
    GEMINI_API_KEY = "AIzaSyDTMu5QsWj8iIG33dzBzWM7Yrjb-H2oaJM"
    
    # Logging Configuration
    LOG_LEVEL = "INFO"
    LOG_DIR = "data/logs"
    LOG_FILE_PATH = "data/logs/ai_job_agent.log"
    
    # Database Configuration
    DATABASE_URL = "sqlite:///data/job_agent_database.db"
    
    # Browser Automation Configuration
    BROWSER_HEADLESS = False
    BROWSER_TIMEOUT = 30000
    SCREENSHOT_DIR = "data/screenshots"
    
    # Multi-Platform Job Portal Configuration
    ENABLED_PLATFORMS = {
        "indeed": True,
        "linkedin": True,
        "remote_co": True,
        "glassdoor": True,
        "ziprecruiter": True,
        "monster": True,
        "dice": True,
        "stackoverflow": True,
        "angel_co": True,
        "wellfound": True
    }
    
    # Advanced Features
    ENABLE_AUTO_APPLY = True
    ENABLE_WEB_BROWSING = True
    ENABLE_CAREER_PORTAL_DISCOVERY = True
    ENABLE_RESUME_OPTIMIZATION = True
    ENABLE_COMPANY_RESEARCH = True
    
    # Application Automation Settings
    AUTO_FILL_FORMS = True
    REQUIRE_HUMAN_APPROVAL = True
    SAVE_APPLICATION_SCREENSHOTS = True
    MAX_APPLICATIONS_PER_DAY = 10
    
    # Web Browsing Settings
    ENABLE_GOOGLE_SEARCH = True
    CAREER_PAGE_KEYWORDS = [
        "careers", "jobs", "opportunities", "positions", "openings",
        "work-with-us", "join-us", "employment", "talent", "hiring",
        "vacancies", "apply", "job-board", "current-openings"
    ]
    
    # Rate Limiting (to avoid being blocked)
    REQUEST_DELAY_MIN = 2
    REQUEST_DELAY_MAX = 5
    CONCURRENT_SCRAPERS = 3
    
    # Platform-Specific Configurations
    PLATFORM_CONFIGS = {
        "indeed": {
            "base_url": "https://indeed.com",
            "search_endpoint": "/jobs",
            "rate_limit": 1,  # seconds between requests
            "max_results_per_page": 50,
            "authentication_required": False
        },
        "linkedin": {
            "base_url": "https://linkedin.com",
            "search_endpoint": "/jobs/search",
            "rate_limit": 3,  # LinkedIn is stricter
            "max_results_per_page": 25,
            "authentication_required": True
        },
        "glassdoor": {
            "base_url": "https://glassdoor.com",
            "search_endpoint": "/Job/jobs.htm",
            "rate_limit": 2,
            "max_results_per_page": 30,
            "authentication_required": False
        },
        "ziprecruiter": {
            "base_url": "https://ziprecruiter.com",
            "search_endpoint": "/jobs/search",
            "rate_limit": 1,
            "max_results_per_page": 40,
            "authentication_required": False
        }
    }
    
    # User Agent Rotation for Anti-Detection
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]
    
    @classmethod
    def get_platform_config(cls, platform: str) -> Dict[str, Any]:
        """Get configuration for a specific platform"""
        return cls.PLATFORM_CONFIGS.get(platform.lower(), {})
    
    @classmethod
    def is_platform_enabled(cls, platform: str) -> bool:
        """Check if a platform is enabled"""
        return cls.ENABLED_PLATFORMS.get(platform.lower(), False)
    
    @classmethod
    def get_enabled_platforms(cls) -> List[str]:
        """Get list of enabled platforms"""
        return [platform for platform, enabled in cls.ENABLED_PLATFORMS.items() if enabled]

# Global instance
enhanced_settings = EnhancedSettings() 