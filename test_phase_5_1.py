#!/usr/bin/env python3
"""
Test script for Phase 5.1 Semantic Analysis functionality
Tests embedding generation and semantic analysis capabilities
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

def test_embedding_service():
    """Test the EmbeddingService functionality."""
    print("🧪 Testing EmbeddingService...")
    
    try:
        from app.services.embedding_service import EmbeddingService
        
        # Initialize service
        service = EmbeddingService()
        print(f"✅ EmbeddingService initialized with model: {service.model_name}")
        print(f"📏 Embedding dimension: {service.get_embedding_dimension()}")
        
        # Test single text encoding
        test_text = "Senior Python Developer position with machine learning experience required"
        embedding = service.encode_text(test_text)
        print(f"✅ Single text embedding: shape {embedding.shape}")
        
        # Test batch encoding
        test_texts = [
            "Python developer with AI/ML experience",
            "Frontend React developer needed",
            "Data scientist with Python and SQL"
        ]
        embeddings = service.encode_texts(test_texts)
        print(f"✅ Batch embeddings: {len(embeddings)} embeddings generated")
        
        # Test similarity
        similarity = service.calculate_similarity(embedding, embeddings[0])
        print(f"✅ Similarity calculation: {similarity:.3f}")
        
        # Test JSON serialization
        json_embedding = service.embedding_to_json(embedding)
        restored = service.embedding_from_json(json_embedding)
        restoration_sim = service.calculate_similarity(embedding, restored)
        print(f"✅ JSON serialization preservation: {restoration_sim:.6f}")
        
        print("🎉 EmbeddingService tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ EmbeddingService test failed: {e}")
        logger.error(f"EmbeddingService test error: {e}", exc_info=True)
        return False

async def test_semantic_analysis_service():
    """Test the SemanticAnalysisService functionality."""
    print("🔍 Testing SemanticAnalysisService...")
    
    try:
        from app.services.semantic_analysis_service import get_semantic_analysis_service
        from app.models.job_posting_models import JobPosting
        
        # Initialize service
        service = get_semantic_analysis_service()
        print("✅ SemanticAnalysisService initialized")
        
        # Create a test job
        test_job = JobPosting(
            id_on_platform="test_123",
            source_platform="test",
            job_url="https://example.com/job/123",
            title="Senior Python Developer",
            company_name="TechCorp",
            full_description_text="""
            We are looking for a Senior Python Developer with experience in machine learning.
            The ideal candidate will have 5+ years of Python experience, knowledge of FastAPI,
            and experience with cloud platforms like AWS. Remote work is available.
            """,
            internal_db_id=1
        )
        
        # Test embedding generation
        print("📊 Testing embedding generation...")
        embeddings_data = await service.generate_job_embeddings(test_job)
        if embeddings_data:
            print("✅ Job embeddings generated successfully")
            test_job.description_embedding = embeddings_data.get('description_embedding')
            test_job.embedding_model = embeddings_data.get('embedding_model')
        
        # Test semantic similarity
        print("🎯 Testing semantic similarity calculation...")
        similarity = service.calculate_semantic_similarity(test_job)
        print(f"✅ Semantic similarity: {similarity:.3f}")
        
        # Test combined scoring
        test_job.relevance_score = 4.2  # Mock AI relevance score
        combined_score = service.calculate_combined_match_score(test_job)
        print(f"✅ Combined match score: {combined_score:.2f}")
        
        # Test complete analysis
        analyzed_job = await service.analyze_job_semantic_match(test_job)
        print(f"✅ Complete analysis: similarity={analyzed_job.semantic_similarity_score:.3f}, combined={analyzed_job.combined_match_score:.2f}")
        
        print("🎉 SemanticAnalysisService tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ SemanticAnalysisService test failed: {e}")
        logger.error(f"SemanticAnalysisService test error: {e}", exc_info=True)
        return False

def test_database_schema():
    """Test database schema updates for semantic analysis."""
    print("🗄️ Testing database schema...")
    
    try:
        from app.services.database_service import add_embedding_columns_if_not_exist
        
        # Test schema update
        add_embedding_columns_if_not_exist()
        print("✅ Database schema update completed")
        
        print("🎉 Database schema tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        logger.error(f"Database schema test error: {e}", exc_info=True)
        return False

async def main():
    """Run all Phase 5.1 tests."""
    print("🚀 Phase 5.1 Semantic Analysis Test Suite\n")
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: EmbeddingService
    if test_embedding_service():
        tests_passed += 1
    
    # Test 2: Database Schema
    if test_database_schema():
        tests_passed += 1
    
    # Test 3: SemanticAnalysisService
    if await test_semantic_analysis_service():
        tests_passed += 1
    
    # Summary
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All Phase 5.1 tests passed! Semantic analysis is ready!")
        print("\n💡 Next steps:")
        print("  1. Run: python main.py ensure-semantic-schema")
        print("  2. Run: python main.py semantic-analysis --target-role 'Your Role'")
        print("  3. Run: python main.py semantic-search 'Your search query'")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 