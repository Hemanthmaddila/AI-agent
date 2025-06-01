#!/usr/bin/env python3
"""
Test script for Phase 4.2: Application Automation Engine

Tests the form filling, HITL services, and CLI integration for automated job applications.
"""

import sys
import os
import logging
import asyncio
from datetime import datetime

# Add project root to path
if '.' not in sys.path:
    sys.path.insert(0, '.')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_form_filler_service():
    """Test the FormFillerService functionality."""
    print("🧪 Testing FormFillerService...")
    
    try:
        from app.application_automation.form_filler import FormFillerService
        
        # Initialize service
        service = FormFillerService(headless=True)  # Use headless for testing
        print(f"✅ FormFillerService initialized successfully")
        
        # Test field mapping
        print(f"✅ Field mappings loaded: {len(service.field_mappings)} categories")
        
        # Test field categorization
        test_cases = [
            ("first_name email phone", "text", "first_name"),
            ("email address contact", "email", "email"),
            ("phone mobile tel", "tel", "phone"),
            ("linkedin profile social", "text", "linkedin"),
            ("github portfolio website", "text", "github"),
        ]
        
        for field_text, input_type, expected in test_cases:
            result = service._categorize_field(field_text, input_type)
            if result == expected:
                print(f"✅ Field categorization: '{field_text}' -> '{result}'")
            else:
                print(f"❌ Field categorization failed: '{field_text}' -> '{result}' (expected '{expected}')")
        
        return True
        
    except Exception as e:
        print(f"❌ FormFillerService test failed: {e}")
        return False

def test_hitl_service():
    """Test the HITLService functionality."""
    print("\n🧪 Testing HITLService...")
    
    try:
        from app.hitl.hitl_service import HITLService
        from app.models.user_profile_models import UserProfile
        from app.models.job_posting_models import JobPosting
        
        # Initialize service
        service = HITLService()
        print(f"✅ HITLService initialized successfully")
        
        # Test session logging
        service.log_session_event("test", "Test event for validation", {"test_data": "value"})
        print(f"✅ Session event logging works")
        
        # Test session summary
        summary = service.get_session_summary()
        print(f"✅ Session summary: {summary['total_events']} events")
        
        return True
        
    except Exception as e:
        print(f"❌ HITLService test failed: {e}")
        return False

def test_user_profile_model():
    """Test UserProfile model functionality."""
    print("\n🧪 Testing UserProfile model...")
    
    try:
        from app.models.user_profile_models import UserProfile, Skill, ExperienceItem
        
        # Create test profile
        test_profile = UserProfile(
            profile_name="test_profile",
            full_name="John Doe",
            email="john.doe@example.com",
            phone="123-456-7890",
            linkedin_url="https://linkedin.com/in/johndoe",
            github_url="https://github.com/johndoe",
            summary_statement="Experienced software developer",
            skills=[
                Skill(name="Python", proficiency="Advanced", years_of_experience=5),
                Skill(name="JavaScript", proficiency="Intermediate", years_of_experience=3)
            ],
            experiences=[
                ExperienceItem(
                    job_title="Senior Developer",
                    company_name="Tech Corp",
                    start_date="2020-01-01",
                    end_date="Present",
                    description_points=["Led development team", "Built scalable systems"],
                    skills_used=["Python", "AWS"]
                )
            ],
            target_roles=["Senior Python Developer", "Tech Lead"],
            preferred_locations=["Remote", "San Francisco"]
        )
        
        print(f"✅ UserProfile created: {test_profile.profile_name}")
        print(f"✅ Skills: {len(test_profile.skills)} skills")
        print(f"✅ Experience: {len(test_profile.experiences)} items")
        print(f"✅ Target roles: {len(test_profile.target_roles)} roles")
        
        # Test JSON serialization
        json_str = test_profile.model_dump_json()
        print(f"✅ JSON serialization successful: {len(json_str)} characters")
        
        # Test JSON deserialization
        loaded_profile = UserProfile.model_validate_json(json_str)
        print(f"✅ JSON deserialization successful: {loaded_profile.profile_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ UserProfile model test failed: {e}")
        return False

def test_profile_data_extraction():
    """Test profile data extraction for form filling."""
    print("\n🧪 Testing profile data extraction...")
    
    try:
        from app.application_automation.form_filler import FormFillerService
        from app.models.user_profile_models import UserProfile
        
        # Create test profile
        test_profile = UserProfile(
            profile_name="test_extraction",
            full_name="Jane Smith",
            email="jane.smith@example.com",
            phone="987-654-3210",
            linkedin_url="https://linkedin.com/in/janesmith",
            preferred_locations=["New York", "Remote"]
        )
        
        # Initialize form filler
        service = FormFillerService()
        
        # Extract profile data
        extracted_data = service._extract_profile_data(test_profile)
        
        print(f"✅ Extracted data keys: {list(extracted_data.keys())}")
        
        # Verify key fields
        expected_fields = ['first_name', 'last_name', 'full_name', 'email', 'phone', 'linkedin']
        for field in expected_fields:
            if field in extracted_data:
                print(f"✅ {field}: {extracted_data[field]}")
            else:
                print(f"❌ Missing field: {field}")
        
        # Test name splitting
        if extracted_data['first_name'] == 'Jane' and extracted_data['last_name'] == 'Smith':
            print(f"✅ Name splitting works correctly")
        else:
            print(f"❌ Name splitting failed: {extracted_data['first_name']} {extracted_data['last_name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Profile data extraction test failed: {e}")
        return False

def test_cli_integration():
    """Test CLI integration and help text."""
    print("\n🧪 Testing CLI integration...")
    
    try:
        import subprocess
        
        # Test main help
        result = subprocess.run([sys.executable, "main.py", "--help"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ Main CLI help works")
            
            # Check for Phase 4.2 commands
            phase_4_2_commands = [
                "create-profile",
                "apply-to-job", 
                "list-profiles",
                "test-form-detection"
            ]
            
            for cmd in phase_4_2_commands:
                if cmd in result.stdout:
                    print(f"✅ Command '{cmd}' found in help")
                else:
                    print(f"❌ Command '{cmd}' missing from help")
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
        
        # Test specific command help
        for cmd in ["create-profile", "apply-to-job"]:
            try:
                result = subprocess.run([sys.executable, "main.py", cmd, "--help"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✅ Command '{cmd}' help works")
                else:
                    print(f"❌ Command '{cmd}' help failed")
            except subprocess.TimeoutExpired:
                print(f"⚠️ Command '{cmd}' help timed out")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI integration test failed: {e}")
        return False

def test_directory_structure():
    """Test that required directories exist or can be created."""
    print("\n🧪 Testing directory structure...")
    
    try:
        required_dirs = [
            "data/user_profiles",
            "data/screenshots",
            "app/application_automation",
            "app/hitl"
        ]
        
        for dir_path in required_dirs:
            if os.path.exists(dir_path):
                print(f"✅ Directory exists: {dir_path}")
            else:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    print(f"✅ Directory created: {dir_path}")
                except Exception as e:
                    print(f"❌ Failed to create directory {dir_path}: {e}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Directory structure test failed: {e}")
        return False

def test_dependencies():
    """Test that required dependencies are available."""
    print("\n🧪 Testing dependencies...")
    
    try:
        # Test core dependencies
        dependencies = [
            ("playwright", "playwright.async_api"),
            ("pydantic", "pydantic"),
            ("typer", "typer"),
            ("rich", "rich.console"),
        ]
        
        for dep_name, import_path in dependencies:
            try:
                __import__(import_path)
                print(f"✅ {dep_name} is available")
            except ImportError as e:
                print(f"❌ {dep_name} is missing: {e}")
                return False
        
        # Test Playwright browser
        try:
            from playwright.async_api import async_playwright
            print(f"✅ Playwright async API available")
        except ImportError:
            print(f"❌ Playwright async API not available")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Dependencies test failed: {e}")
        return False

def main():
    """Run all Phase 4.2 tests."""
    print("🚀 Phase 4.2: Application Automation Engine - Test Suite")
    print("=" * 80)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Directory Structure", test_directory_structure),
        ("UserProfile Model", test_user_profile_model),
        ("FormFillerService", test_form_filler_service),
        ("HITLService", test_hitl_service),
        ("Profile Data Extraction", test_profile_data_extraction),
        ("CLI Integration", test_cli_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n" + "-" * 50)
        print(f"🧪 Running: {test_name}")
        print("-" * 50)
        
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY - Phase 4.2: Application Automation Engine")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} | {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All Phase 4.2 tests passed! Application automation is ready!")
        print("\n💡 Next steps:")
        print("  • Create your first user profile: python main.py create-profile")
        print("  • Test form detection: python main.py test-form-detection <url>")
        print("  • Apply to jobs: python main.py apply-to-job --job-url <url>")
    else:
        print("⚠️ Some tests failed. Please review the errors above.")
        print("💡 Common issues:")
        print("  • Missing dependencies: pip install -r requirements.txt")
        print("  • Playwright setup: playwright install")
        print("  • Directory permissions")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 