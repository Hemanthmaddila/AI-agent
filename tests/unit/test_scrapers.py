"""
Unit tests for the scrapers module
Tests the multi-site job discovery functionality including Stack Overflow, LinkedIn, Indeed, and Remote.co scrapers
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Add project root to path
import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app.services.scrapers.base_scraper import JobScraper, ScraperConfig, ScraperResult
from app.services.scrapers.scraper_manager import ScraperManager, MultiSiteSearchResult
from app.services.scrapers.stackoverflow_scraper import StackOverflowJobsScraper
from app.services.scrapers import create_scraper_manager, get_available_scrapers
from app.models.job_posting_models import JobPosting

class TestScraperConfig:
    """Test ScraperConfig functionality"""
    
    def test_scraper_config_default_values(self):
        """Test ScraperConfig default values"""
        config = ScraperConfig()
        assert config.max_results == 10
        assert config.delay_range == (2, 5)
        assert config.timeout == 30000
        assert config.headless == True
        assert config.user_agent_rotation == True
        assert config.respect_robots_txt == True
        assert config.max_retries == 3
    
    def test_scraper_config_custom_values(self):
        """Test ScraperConfig with custom values"""
        config = ScraperConfig(
            max_results=20,
            delay_range=(1, 3),
            timeout=15000,
            headless=False
        )
        assert config.max_results == 20
        assert config.delay_range == (1, 3)
        assert config.timeout == 15000
        assert config.headless == False

class TestScraperResult:
    """Test ScraperResult functionality"""
    
    def test_scraper_result_success(self):
        """Test successful scraper result"""
        mock_jobs = [
            JobPosting(
                job_url="https://test.com/job1",
                title="Python Developer",
                company_name="Test Corp",
                location_text="Remote",
                source_platform="Test",
                full_description_raw="Test job description",
                processing_status="pending"
            )
        ]
        
        result = ScraperResult(
            jobs=mock_jobs,
            source="Test Scraper",
            success=True,
            jobs_found=1,
            execution_time=5.0
        )
        
        assert result.success == True
        assert len(result.jobs) == 1
        assert result.jobs_found == 1
        assert result.execution_time == 5.0
        assert result.error_message is None
    
    def test_scraper_result_failure(self):
        """Test failed scraper result"""
        result = ScraperResult(
            jobs=[],
            source="Test Scraper",
            success=False,
            error_message="Connection timeout",
            jobs_found=0,
            execution_time=10.0
        )
        
        assert result.success == False
        assert len(result.jobs) == 0
        assert result.error_message == "Connection timeout"

class TestStackOverflowJobsScraper:
    """Test Stack Overflow Jobs scraper"""
    
    def test_initialization(self):
        """Test scraper initialization"""
        scraper = StackOverflowJobsScraper()
        assert scraper.site_name == "Stack Overflow Jobs"
        assert scraper.base_url == "https://stackoverflow.com/jobs"
    
    def test_build_search_url(self):
        """Test search URL building"""
        scraper = StackOverflowJobsScraper()
        
        # Test basic URL
        url = scraper._build_search_url("Python Developer")
        assert "q=Python+Developer" in url
        assert "l=Remote" in url
        assert "sort=p" in url
        
        # Test with location
        url = scraper._build_search_url("Python Developer", "San Francisco")
        assert "q=Python+Developer" in url
        assert "l=San+Francisco" in url
    
    def test_mock_job_generation(self):
        """Test mock job generation fallback"""
        scraper = StackOverflowJobsScraper()
        mock_jobs = scraper._generate_mock_jobs("Python Developer", 3)
        
        assert len(mock_jobs) == 3
        for job in mock_jobs:
            assert isinstance(job, JobPosting)
            assert job.source_platform == "Stack Overflow Jobs_Mock"
            assert "Python" in job.title or "Developer" in job.title

class TestScraperManager:
    """Test ScraperManager functionality"""
    
    def test_initialization(self):
        """Test scraper manager initialization"""
        manager = ScraperManager()
        assert len(manager.scrapers) == 0
        assert len(manager.enabled_sources) == 0
    
    def test_register_scraper(self):
        """Test scraper registration"""
        manager = ScraperManager()
        mock_scraper = Mock()
        mock_scraper.site_name = "Test Scraper"
        
        manager.register_scraper(mock_scraper, enabled=True)
        
        assert "test scraper" in manager.scrapers
        assert "test scraper" in manager.enabled_sources
    
    def test_enable_disable_source(self):
        """Test enabling and disabling sources"""
        manager = ScraperManager()
        mock_scraper = Mock()
        mock_scraper.site_name = "Test Scraper"
        
        manager.register_scraper(mock_scraper, enabled=False)
        assert "test scraper" not in manager.enabled_sources
        
        manager.enable_source("test scraper")
        assert "test scraper" in manager.enabled_sources
        
        manager.disable_source("test scraper")
        assert "test scraper" not in manager.enabled_sources
    
    def test_deduplication(self):
        """Test job deduplication functionality"""
        manager = ScraperManager()
        
        # Create duplicate jobs
        job1 = JobPosting(
            job_url="https://test.com/job1",
            title="Python Developer",
            company_name="Test Corp",
            location_text="Remote",
            source_platform="Test1",
            full_description_raw="Test description",
            processing_status="pending"
        )
        
        job2 = JobPosting(
            job_url="https://test.com/job1",  # Same URL
            title="Python Developer",
            company_name="Test Corp",
            location_text="Remote",
            source_platform="Test2",
            full_description_raw="Test description",
            processing_status="pending"
        )
        
        job3 = JobPosting(
            job_url="https://test.com/job2",  # Different URL
            title="Java Developer",
            company_name="Test Corp",
            location_text="Remote",
            source_platform="Test1",
            full_description_raw="Different description",
            processing_status="pending"
        )
        
        jobs = [job1, job2, job3]
        unique_jobs, duplicates_removed = manager._deduplicate_jobs(jobs)
        
        assert len(unique_jobs) == 2  # job1 and job3
        assert duplicates_removed == 1  # job2 is duplicate of job1

class TestScraperFactoryFunctions:
    """Test factory functions for scraper creation"""
    
    def test_get_available_scrapers(self):
        """Test getting available scrapers information"""
        available = get_available_scrapers()
        
        assert 'remote.co' in available
        assert 'linkedin' in available
        assert 'indeed' in available
        assert 'stackoverflow' in available
        
        # Check structure
        for source, info in available.items():
            assert 'name' in info
            assert 'description' in info
            assert 'authentication_required' in info
            assert 'reliability' in info
    
    def test_create_scraper_manager(self):
        """Test scraper manager creation"""
        # Test with default sources
        manager = create_scraper_manager()
        enabled = manager.get_enabled_sources()
        
        assert 'remote.co' in enabled
        assert 'indeed' in enabled
        assert 'stackoverflow' in enabled
        
        # Test with custom sources
        manager = create_scraper_manager(enabled_sources=['stackoverflow'])
        enabled = manager.get_enabled_sources()
        
        assert 'stackoverflow' in enabled
        assert len(enabled) == 1

class TestAsyncScraperOperations:
    """Test asynchronous scraper operations"""
    
    @pytest.mark.asyncio
    async def test_stackoverflow_search_with_mock_fallback(self):
        """Test Stack Overflow scraper with mock data fallback"""
        scraper = StackOverflowJobsScraper()
        
        # Mock the browser setup to avoid actual browser usage in tests
        with patch.object(scraper, '_setup_browser') as mock_browser, \
             patch.object(scraper, '_setup_page') as mock_page, \
             patch.object(scraper, '_extract_job_data') as mock_extract:
            
            # Setup mocks
            mock_browser.return_value = AsyncMock()
            mock_page.return_value = AsyncMock()
            mock_extract.return_value = []  # No jobs found, will trigger fallback
            
            result = await scraper.search_jobs("Python Developer", num_results=2)
            
            assert result.success == True
            assert len(result.jobs) == 2
            assert result.source == "Stack Overflow Jobs_Mock"
    
    @pytest.mark.asyncio
    async def test_scraper_manager_parallel_search(self):
        """Test parallel search across multiple scrapers"""
        manager = ScraperManager()
        
        # Create mock scrapers
        mock_scraper1 = AsyncMock()
        mock_scraper1.site_name = "Test Scraper 1"
        mock_scraper1.search_jobs.return_value = ScraperResult(
            jobs=[JobPosting(
                job_url="https://test1.com/job1",
                title="Python Dev 1",
                company_name="Company 1",
                location_text="Remote",
                source_platform="Test1",
                full_description_raw="Description 1",
                processing_status="pending"
            )],
            source="Test1",
            success=True,
            jobs_found=1,
            execution_time=1.0
        )
        mock_scraper1.cleanup = AsyncMock()
        
        mock_scraper2 = AsyncMock()
        mock_scraper2.site_name = "Test Scraper 2"
        mock_scraper2.search_jobs.return_value = ScraperResult(
            jobs=[JobPosting(
                job_url="https://test2.com/job1",
                title="Python Dev 2",
                company_name="Company 2",
                location_text="Remote",
                source_platform="Test2",
                full_description_raw="Description 2",
                processing_status="pending"
            )],
            source="Test2",
            success=True,
            jobs_found=1,
            execution_time=2.0
        )
        mock_scraper2.cleanup = AsyncMock()
        
        # Register scrapers
        manager.scrapers['test1'] = mock_scraper1
        manager.scrapers['test2'] = mock_scraper2
        manager.enabled_sources.add('test1')
        manager.enabled_sources.add('test2')
        
        # Execute search
        result = await manager.search_all_sources(
            keywords="Python Developer",
            num_results_per_source=1,
            sources=['test1', 'test2']
        )
        
        assert isinstance(result, MultiSiteSearchResult)
        assert result.total_found == 2
        assert len(result.successful_sources) == 2
        assert len(result.failed_sources) == 0
        assert result.duplicates_removed == 0

class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_scraper_error_handling(self):
        """Test scraper error handling"""
        manager = ScraperManager()
        
        # Create failing mock scraper
        mock_scraper = AsyncMock()
        mock_scraper.site_name = "Failing Scraper"
        mock_scraper.search_jobs.side_effect = Exception("Network error")
        mock_scraper.cleanup = AsyncMock()
        
        manager.scrapers['failing'] = mock_scraper
        manager.enabled_sources.add('failing')
        
        result = await manager.search_all_sources(
            keywords="Python Developer",
            sources=['failing']
        )
        
        assert result.total_found == 0
        assert len(result.failed_sources) == 1
        assert 'failing' in result.failed_sources
    
    def test_invalid_source_handling(self):
        """Test handling of invalid sources"""
        manager = create_scraper_manager(enabled_sources=['invalid_source'])
        
        # Should not include invalid source
        enabled = manager.get_enabled_sources()
        assert 'invalid_source' not in enabled

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"]) 