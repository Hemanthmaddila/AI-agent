"""
Integration tests for CLI commands
Tests the full workflow of job discovery, analysis, and application logging
"""
import pytest
import subprocess
import sys
import os
from unittest.mock import patch, Mock

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

class TestCLICommands:
    """Test CLI command functionality"""
    
    def test_cli_help_command(self):
        """Test that help command works"""
        result = subprocess.run([
            sys.executable, "main.py", "--help"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 0
        assert "AI Job Application Agent" in result.stdout
        assert "Commands:" in result.stdout
    
    def test_find_jobs_multi_help(self):
        """Test find-jobs-multi help command"""
        result = subprocess.run([
            sys.executable, "main.py", "find-jobs-multi", "--help"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 0
        assert "Multi-Site Job Discovery" in result.stdout
        assert "--sources" in result.stdout
        assert "--results" in result.stdout
    
    def test_analyze_jobs_help(self):
        """Test analyze-jobs help command"""
        result = subprocess.run([
            sys.executable, "main.py", "analyze-jobs", "--help"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 0
        assert "AI" in result.stdout or "analyze" in result.stdout.lower()
    
    def test_view_applications_help(self):
        """Test view-applications help command"""
        result = subprocess.run([
            sys.executable, "main.py", "view-applications", "--help"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 0
        assert "applications" in result.stdout.lower()
    
    def test_linkedin_session_info_help(self):
        """Test LinkedIn session commands help"""
        result = subprocess.run([
            sys.executable, "main.py", "linkedin-session-info", "--help"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 0
        assert "LinkedIn" in result.stdout or "session" in result.stdout.lower()

class TestCLIValidation:
    """Test CLI input validation"""
    
    def test_find_jobs_multi_invalid_source(self):
        """Test find-jobs-multi with invalid source"""
        result = subprocess.run([
            sys.executable, "main.py", "find-jobs-multi", 
            "Python Developer", "--sources", "invalid_source", "--results", "1"
        ], capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 1
        assert "Invalid sources" in result.stdout or "invalid" in result.stdout.lower()
    
    def test_find_jobs_multi_valid_sources(self):
        """Test find-jobs-multi with valid sources"""
        # Use a very short test to avoid long execution times
        result = subprocess.run([
            sys.executable, "main.py", "find-jobs-multi", 
            "Test", "--sources", "stackoverflow", "--results", "1"
        ], capture_output=True, text=True, cwd=project_root, timeout=120)
        
        # Should not fail with validation error (may timeout or succeed)
        # We're mainly testing that the command starts correctly
        assert "Invalid sources" not in result.stdout

class TestCLIConfigurationErrors:
    """Test CLI behavior with configuration issues"""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_analyze_jobs_without_gemini_key(self):
        """Test analyze-jobs command without Gemini API key"""
        result = subprocess.run([
            sys.executable, "main.py", "analyze-jobs", "--max-jobs", "1"
        ], capture_output=True, text=True, cwd=project_root, env={})
        
        assert result.returncode == 1
        assert "GEMINI_API_KEY" in result.stdout

class TestCLIWorkflow:
    """Test CLI workflow scenarios"""
    
    def test_log_application_missing_params(self):
        """Test log-application with missing required parameters"""
        result = subprocess.run([
            sys.executable, "main.py", "log-application", 
            "https://test.com/job", "/nonexistent/resume.pdf"
        ], capture_output=True, text=True, cwd=project_root)
        
        # Should handle missing resume file gracefully
        assert result.returncode in [0, 1]  # May succeed with warning or fail

class TestCLIImportValidation:
    """Test that all required modules can be imported"""
    
    def test_main_imports(self):
        """Test that main.py imports work correctly"""
        result = subprocess.run([
            sys.executable, "-c", 
            "import sys; sys.path.append('{}'); import main".format(project_root)
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode != 0:
            print("Import error stdout:", result.stdout)
            print("Import error stderr:", result.stderr)
        
        assert result.returncode == 0, f"Failed to import main module: {result.stderr}"
    
    def test_scraper_imports(self):
        """Test that scraper modules import correctly"""
        result = subprocess.run([
            sys.executable, "-c", 
            f"import sys; sys.path.append('{project_root}'); from app.services.scrapers import get_available_scrapers; print('Success')"
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode != 0:
            print("Scraper import error stdout:", result.stdout)
            print("Scraper import error stderr:", result.stderr)
        
        assert result.returncode == 0, f"Failed to import scrapers: {result.stderr}"
        assert "Success" in result.stdout

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 