#!/usr/bin/env python3
"""
Test script for Google Gemini API connectivity.
This script verifies that the API key is working and the Gemini model is accessible.
"""

import sys
import os

# Add the project root to Python path so we can import our modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config.settings import GEMINI_API_KEY
    import google.generativeai as genai
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you've installed all dependencies with: pip install -r requirements.txt")
    sys.exit(1)

def test_gemini_api():
    """Test the Gemini API connectivity and basic functionality."""
    
    print("🤖 Testing Google Gemini API...")
    print("=" * 50)
    
    # Check if API key is loaded
    if not GEMINI_API_KEY:
        print("❌ FAILED: GEMINI_API_KEY not found in environment variables.")
        print("Please check your .env file and ensure GEMINI_API_KEY is set.")
        return False
    
    print(f"✅ API Key loaded: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-4:]}")
    
    try:
        # Configure the API
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ API configured successfully")
        
        # List available models
        print("\n🔍 Available Gemini models:")
        models = genai.list_models()
        gemini_models = []
        
        # Prefer newer models and avoid deprecated ones
        preferred_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash']
        
        for model in models:
            if 'gemini' in model.name.lower() and 'vision' not in model.name.lower():
                gemini_models.append(model.name)
                print(f"  - {model.name}")
        
        if not gemini_models:
            print("❌ No Gemini models found")
            return False
        
        # Select the best available model
        selected_model = None
        for preferred in preferred_models:
            for available_model in gemini_models:
                if preferred in available_model:
                    selected_model = available_model
                    break
            if selected_model:
                break
        
        # If no preferred model found, use the first non-vision model
        if not selected_model:
            for model_name in gemini_models:
                if 'vision' not in model_name.lower():
                    selected_model = model_name
                    break
        
        if not selected_model:
            print("❌ No suitable Gemini model found")
            return False
        
        # Test with a simple prompt
        print(f"\n🧪 Testing with model: {selected_model}")
        model = genai.GenerativeModel(selected_model)
        
        test_prompt = "Hello! Please respond with 'API test successful' if you can read this message."
        print(f"Sending test prompt: '{test_prompt}'")
        
        response = model.generate_content(test_prompt)
        print(f"✅ Response received: {response.text}")
        
        # Verify the response contains expected text
        if "API test successful" in response.text or "successful" in response.text.lower():
            print("✅ API test completed successfully!")
            return True
        else:
            print("⚠️  API responded but with unexpected content.")
            return True  # Still consider it successful since we got a response
            
    except Exception as e:
        print(f"❌ FAILED: Error testing Gemini API: {e}")
        return False

def test_specific_model(model_name="gemini-1.5-flash"):
    """Test a specific Gemini model for job application use cases."""
    
    print(f"\n🎯 Testing specific model: {model_name}")
    print("=" * 50)
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name)
        
        # Test prompt relevant to job applications
        job_prompt = """
        You are an AI assistant helping with job applications. 
        Please analyze this job posting and tell me if it's suitable for a Python developer:
        
        "Software Engineer - Python
        Requirements: 3+ years Python experience, knowledge of Django, REST APIs.
        Remote work available."
        
        Respond with 'SUITABLE' or 'NOT SUITABLE' followed by a brief reason.
        """
        
        print("Testing job analysis capability...")
        response = model.generate_content(job_prompt)
        print(f"✅ Job analysis response: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing specific model {model_name}: {e}")
        print("💡 This model might not be available with your API key plan.")
        return False

if __name__ == "__main__":
    print("🚀 Starting Gemini API Test Suite")
    print("=" * 60)
    
    # Run basic API test
    basic_test_success = test_gemini_api()
    
    if basic_test_success:
        # Run specific model test
        specific_test_success = test_specific_model()
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY:")
        print(f"  Basic API Test: {'✅ PASSED' if basic_test_success else '❌ FAILED'}")
        print(f"  Specific Model Test: {'✅ PASSED' if specific_test_success else '❌ FAILED'}")
        
        if basic_test_success:
            print("\n🎉 Gemini API is ready for use in your AI Job Application Agent!")
        else:
            print("\n❌ Please fix the API issues before proceeding.")
    else:
        print("\n❌ Basic API test failed. Please check your configuration.")
    
    print("\n" + "=" * 60) 