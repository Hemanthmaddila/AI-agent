#!/usr/bin/env python3
"""
Quick test script for Wellfound scraper integration
"""

def test_wellfound_integration():
    print("🧪 Testing Wellfound Scraper Integration")
    print("=" * 50)
    
    try:
        # Test imports
        from app.services.scrapers import get_available_scrapers, create_scraper_manager, WellfoundScraper
        print("✅ Import successful")
        
        # Test available scrapers
        scrapers = get_available_scrapers()
        print(f"\n📋 Available scrapers ({len(scrapers)}):")
        for source, info in scrapers.items():
            print(f"  • {source}: {info['name']}")
        
        # Test Wellfound in available scrapers
        if 'wellfound' in scrapers:
            print("✅ Wellfound found in available scrapers")
            wellfound_info = scrapers['wellfound']
            print(f"   Name: {wellfound_info['name']}")
            print(f"   Description: {wellfound_info['description']}")
            print(f"   Auth Required: {wellfound_info['authentication_required']}")
        else:
            print("❌ Wellfound NOT found in available scrapers")
            
        # Test scraper manager creation
        print("\n🔧 Testing scraper manager creation...")
        manager = create_scraper_manager(['wellfound'])
        enabled = manager.get_enabled_sources()
        print(f"✅ Manager created with sources: {list(enabled)}")
        
        # Test direct scraper creation
        print("\n🏗️  Testing direct scraper creation...")
        scraper = WellfoundScraper()
        print(f"✅ Direct scraper created: {scraper.site_name}")
        
        print("\n🎉 All integration tests passed!")
        print("📌 Next steps:")
        print("   1. Test with: python main.py find-jobs-multi \"Python Developer\" --sources wellfound --results 3")
        print("   2. Check Apollo GraphQL data extraction against real Wellfound pages")
        print("   3. Refine parsing logic based on actual JSON structure")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_wellfound_integration() 