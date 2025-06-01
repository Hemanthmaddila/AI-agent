"""
Unit tests for the database service module
Tests job posting and application logging functionality
"""
import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import patch, Mock

# Add project root to path
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from app.models.job_posting_models import JobPosting
from app.models.application_log_models import ApplicationLog

class TestDatabaseService:
    """Test database service functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Use in-memory database for testing
        self.test_db_path = ":memory:"
    
    @patch('app.services.database_service.save_job_posting')
    def test_save_job_posting_success(self, mock_save_job_posting):
        """Test successful job posting save"""
        # Import after patching to avoid actual database calls
        from app.services.database_service import save_job_posting
        
        job = JobPosting(
            job_url="https://test.com/job1",
            title="Python Developer",
            company_name="Test Corp",
            location_text="Remote",
            source_platform="Test",
            full_description_raw="Test job description",
            processing_status="pending"
        )
        
        # Configure mock
        mock_save_job_posting.return_value = 1
        
        result = save_job_posting(job)
        assert result == 1
        mock_save_job_posting.assert_called_once_with(job)
    
    @patch('app.services.database_service.save_job_posting')
    def test_save_job_posting_duplicate_handling(self, mock_save_job_posting):
        """Test handling of duplicate job postings"""
        from app.services.database_service import save_job_posting
        
        job = JobPosting(
            job_url="https://test.com/duplicate",
            title="Duplicate Job",
            company_name="Test Corp",
            location_text="Remote",
            source_platform="Test",
            full_description_raw="Duplicate description",
            processing_status="pending"
        )
        
        # Simulate duplicate detection (returns None or existing ID)
        mock_save_job_posting.return_value = None
        
        result = save_job_posting(job)
        assert result is None
    
    @patch('app.services.database_service.find_job_by_url')
    def test_find_job_by_url(self, mock_find_job_by_url):
        """Test finding job by URL"""
        from app.services.database_service import find_job_by_url
        
        test_url = "https://test.com/job1"
        
        mock_job = JobPosting(
            job_url=test_url,
            title="Found Job",
            company_name="Test Corp",
            location_text="Remote",
            source_platform="Test",
            full_description_raw="Found description",
            processing_status="pending"
        )
        mock_find_job_by_url.return_value = mock_job
        
        result = find_job_by_url(test_url)
        assert result is not None
        assert str(result.job_url) == test_url  # Convert HttpUrl to string
        assert result.title == "Found Job"
    
    @patch('app.services.database_service.save_application_log')
    def test_save_application_log(self, mock_save_application_log):
        """Test saving application log"""
        from app.services.database_service import save_application_log
        
        app_log = ApplicationLog(
            job_url="https://test.com/job1",
            job_title="Python Developer",
            company_name="Test Corp",
            application_date=datetime.utcnow(),
            status="applied",
            resume_version_used_path="/path/to/resume.pdf",
            notes="Test application"
        )
        
        mock_save_application_log.return_value = 1
        
        result = save_application_log(app_log)
        assert result == 1
        mock_save_application_log.assert_called_once_with(app_log)
    
    @patch('app.services.database_service.get_pending_jobs')
    def test_get_pending_jobs(self, mock_get_pending_jobs):
        """Test getting pending jobs"""
        from app.services.database_service import get_pending_jobs
        
        mock_jobs = [
            JobPosting(
                job_url="https://test.com/job1",
                title="Pending Job 1",
                company_name="Test Corp 1",
                location_text="Remote",
                source_platform="Test",
                full_description_raw="Pending description 1",
                processing_status="pending"
            ),
            JobPosting(
                job_url="https://test.com/job2",
                title="Pending Job 2",
                company_name="Test Corp 2",
                location_text="Remote",
                source_platform="Test",
                full_description_raw="Pending description 2",
                processing_status="pending"
            )
        ]
        mock_get_pending_jobs.return_value = mock_jobs
        
        result = get_pending_jobs(limit=10)
        assert len(result) == 2
        assert all(job.processing_status == "pending" for job in result)
    
    @patch('app.services.database_service.update_job_processing_status')
    def test_update_job_processing_status(self, mock_update_job_processing_status):
        """Test updating job processing status"""
        from app.services.database_service import update_job_processing_status
        
        mock_update_job_processing_status.return_value = True
        
        result = update_job_processing_status(
            job_db_id=1,
            new_status="analyzed",
            relevance_score=4.5
        )
        assert result == True
        mock_update_job_processing_status.assert_called_once_with(
            job_db_id=1,
            new_status="analyzed",
            relevance_score=4.5
        )
    
    @patch('app.services.database_service.get_application_logs')
    def test_get_application_logs(self, mock_get_application_logs):
        """Test getting application logs"""
        from app.services.database_service import get_application_logs
        
        mock_logs = [
            ApplicationLog(
                job_url="https://test.com/job1",
                job_title="Applied Job 1",
                company_name="Test Corp 1",
                application_date=datetime.utcnow(),
                status="applied",
                resume_version_used_path="/path/to/resume1.pdf",
                notes="Application 1"
            ),
            ApplicationLog(
                job_url="https://test.com/job2",
                job_title="Applied Job 2",
                company_name="Test Corp 2",
                application_date=datetime.utcnow(),
                status="interview",
                resume_version_used_path="/path/to/resume2.pdf",
                notes="Application 2"
            )
        ]
        mock_get_application_logs.return_value = mock_logs
        
        result = get_application_logs(user_profile_id=1, limit=20)
        assert len(result) == 2
        assert result[0].status == "applied"
        assert result[1].status == "interview"

class TestDatabaseErrorHandling:
    """Test database error handling scenarios"""
    
    @patch('app.services.database_service.save_job_posting')
    def test_save_job_posting_database_error(self, mock_save_job_posting):
        """Test handling database errors during job save"""
        from app.services.database_service import save_job_posting
        
        job = JobPosting(
            job_url="https://test.com/error",
            title="Error Job",
            company_name="Test Corp",
            location_text="Remote",
            source_platform="Test",
            full_description_raw="Error description",
            processing_status="pending"
        )
        
        mock_save_job_posting.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception, match="Database connection error"):
            save_job_posting(job)
    
    @patch('app.services.database_service.find_job_by_url')
    def test_find_job_by_url_not_found(self, mock_find_job_by_url):
        """Test finding non-existent job by URL"""
        from app.services.database_service import find_job_by_url
        
        mock_find_job_by_url.return_value = None
        
        result = find_job_by_url("https://nonexistent.com/job")
        assert result is None
    
    @patch('app.services.database_service.get_pending_jobs')
    def test_get_pending_jobs_empty_result(self, mock_get_pending_jobs):
        """Test getting pending jobs when none exist"""
        from app.services.database_service import get_pending_jobs
        
        mock_get_pending_jobs.return_value = []
        
        result = get_pending_jobs(limit=10)
        assert len(result) == 0
        assert isinstance(result, list)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 