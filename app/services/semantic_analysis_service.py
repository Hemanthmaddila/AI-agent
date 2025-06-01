"""
Semantic Analysis Service for AI Job Application Agent
Provides advanced semantic job matching using embeddings and enhanced scoring.

Phase 5.1: Intelligent Job Matching with Semantic Embeddings
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np

from .embedding_service import get_embedding_service, EmbeddingService
from . import database_service
from .gemini_service import GeminiService
from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

class SemanticAnalysisService:
    """
    Advanced semantic analysis service that combines embeddings with AI analysis
    for intelligent job matching and scoring.
    """
    
    def __init__(self, 
                 embedding_model: str = 'all-MiniLM-L6-v2',
                 gemini_service: Optional[GeminiService] = None):
        """
        Initialize the semantic analysis service.
        
        Args:
            embedding_model: Name of the sentence-transformers model to use
            gemini_service: Gemini AI service instance
        """
        self.embedding_service = get_embedding_service(embedding_model)
        self.gemini_service = gemini_service or GeminiService()
        
        # Default user profile for testing (in production, this would come from user data)
        self.default_user_profile = {
            "target_role": "Software Engineer",
            "experience_years": 5,
            "skills": ["Python", "JavaScript", "React", "FastAPI", "PostgreSQL", "AWS"],
            "preferred_locations": ["Remote", "San Francisco", "New York"],
            "resume_text": """
            Experienced Software Engineer with 5 years of expertise in full-stack development.
            Skilled in Python, JavaScript, React, and cloud technologies. 
            Strong background in building scalable web applications and RESTful APIs.
            Experience with agile methodologies and collaborative development.
            """
        }
        
        logger.info(f"SemanticAnalysisService initialized with model: {embedding_model}")
    
    async def generate_job_embeddings(self, job: JobPosting) -> Dict[str, Any]:
        """
        Generate embeddings for a job posting's title and description.
        
        Args:
            job: JobPosting instance
            
        Returns:
            Dictionary with embedding data and metadata
        """
        try:
            # Prepare texts for embedding
            title_text = job.title or ""
            description_text = job.full_description_text or job.full_description_raw or ""
            
            if not title_text and not description_text:
                logger.warning(f"No text content found for job {job.id_on_platform}")
                return {}
            
            # Generate embeddings
            embeddings_data = {}
            
            if title_text:
                title_embedding = await self.embedding_service.encode_text_async(title_text)
                embeddings_data["title_embedding"] = self.embedding_service.embedding_to_json(title_embedding)
            
            if description_text:
                desc_embedding = await self.embedding_service.encode_text_async(description_text)
                embeddings_data["description_embedding"] = self.embedding_service.embedding_to_json(desc_embedding)
            
            # Add metadata
            embeddings_data.update({
                "embedding_model": self.embedding_service.model_name,
                "embedding_generated_at": datetime.utcnow()
            })
            
            logger.debug(f"Generated embeddings for job {job.id_on_platform}")
            return embeddings_data
            
        except Exception as e:
            logger.error(f"Error generating embeddings for job {job.id_on_platform}: {e}")
            return {}
    
    def calculate_semantic_similarity(self, job: JobPosting, user_profile: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate semantic similarity between a job and user profile.
        
        Args:
            job: JobPosting with embeddings
            user_profile: User profile dictionary (uses default if None)
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            profile = user_profile or self.default_user_profile
            
            # Generate user profile embedding
            user_text = f"{profile.get('target_role', '')} {profile.get('resume_text', '')}"
            user_embedding = self.embedding_service.encode_text(user_text)
            
            # Get job embeddings
            if not job.description_embedding:
                logger.warning(f"No description embedding for job {job.id_on_platform}")
                return 0.0
            
            job_embedding = self.embedding_service.embedding_from_json(job.description_embedding)
            
            # Calculate similarity
            similarity = self.embedding_service.calculate_similarity(user_embedding, job_embedding)
            return max(0.0, min(1.0, similarity))  # Ensure 0-1 range
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity for job {job.id_on_platform}: {e}")
            return 0.0
    
    def calculate_combined_match_score(self, job: JobPosting, user_profile: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate a combined match score using AI relevance + semantic similarity.
        
        Args:
            job: JobPosting instance
            user_profile: User profile dictionary
            
        Returns:
            Combined score (typically 1-5 scale to match AI relevance)
        """
        try:
            # Get individual scores
            ai_relevance = job.relevance_score or 0.0
            semantic_similarity = job.semantic_similarity_score or self.calculate_semantic_similarity(job, user_profile)
            
            # Combine scores (weighted average)
            # AI relevance weight: 0.6, Semantic similarity weight: 0.4
            # Convert semantic similarity (0-1) to relevance scale (1-5)
            semantic_on_relevance_scale = 1 + (semantic_similarity * 4)  # Maps 0-1 to 1-5
            
            combined_score = (ai_relevance * 0.6) + (semantic_on_relevance_scale * 0.4)
            
            return round(combined_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating combined match score for job {job.id_on_platform}: {e}")
            return 0.0
    
    async def analyze_job_semantic_match(self, job: JobPosting, user_profile: Optional[Dict[str, Any]] = None) -> JobPosting:
        """
        Perform complete semantic analysis on a job posting.
        
        Args:
            job: JobPosting instance
            user_profile: User profile dictionary
            
        Returns:
            Updated JobPosting with semantic analysis data
        """
        try:
            # Generate embeddings if not present
            if not job.description_embedding:
                embeddings_data = await self.generate_job_embeddings(job)
                if embeddings_data:
                    for key, value in embeddings_data.items():
                        setattr(job, key, value)
                    
                    # Save embeddings to database
                    if job.internal_db_id and embeddings_data.get('description_embedding'):
                        from app.services.database_service import save_job_embeddings
                        save_job_embeddings(
                            job.internal_db_id,
                            title_embedding=embeddings_data.get('title_embedding'),
                            description_embedding=embeddings_data.get('description_embedding'),
                            model_name=embeddings_data.get('embedding_model')
                        )
            
            # Calculate semantic similarity
            if job.description_embedding:
                semantic_similarity = self.calculate_semantic_similarity(job, user_profile)
                job.semantic_similarity_score = semantic_similarity
                
                # Calculate combined score
                combined_score = self.calculate_combined_match_score(job, user_profile)
                job.combined_match_score = combined_score
                
                # Update processing status
                job.processing_status = "embedded"
                
                # Save semantic scores to database
                if job.internal_db_id:
                    from app.services.database_service import update_semantic_scores
                    update_semantic_scores(
                        job.internal_db_id,
                        semantic_similarity_score=semantic_similarity,
                        combined_match_score=combined_score
                    )
                
                logger.debug(f"Semantic analysis complete for job {job.id_on_platform}: "
                           f"similarity={semantic_similarity:.3f}, combined_score={combined_score:.2f}")
            
            return job
            
        except Exception as e:
            logger.error(f"Error in semantic analysis for job {job.id_on_platform}: {e}")
            return job
    
    async def batch_analyze_jobs(self, jobs: List[JobPosting], user_profile: Optional[Dict[str, Any]] = None) -> List[JobPosting]:
        """
        Perform semantic analysis on multiple jobs efficiently.
        
        Args:
            jobs: List of JobPosting instances
            user_profile: User profile dictionary
            
        Returns:
            List of updated JobPosting instances
        """
        logger.info(f"Starting batch semantic analysis for {len(jobs)} jobs")
        
        # Process jobs in parallel with controlled concurrency
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent analyses
        
        async def analyze_single_job(job):
            async with semaphore:
                return await self.analyze_job_semantic_match(job, user_profile)
        
        # Run analyses concurrently
        analyzed_jobs = await asyncio.gather(
            *[analyze_single_job(job) for job in jobs],
            return_exceptions=True
        )
        
        # Filter out exceptions and return successful analyses
        successful_jobs = []
        for i, result in enumerate(analyzed_jobs):
            if isinstance(result, JobPosting):
                successful_jobs.append(result)
            else:
                logger.error(f"Failed to analyze job {i}: {result}")
                successful_jobs.append(jobs[i])  # Return original job
        
        logger.info(f"Completed batch semantic analysis: {len(successful_jobs)} jobs processed")
        return successful_jobs
    
    def get_top_matches(self, jobs: List[JobPosting], limit: int = 10, min_combined_score: float = 3.0) -> List[JobPosting]:
        """
        Get top job matches based on combined match score.
        
        Args:
            jobs: List of JobPosting instances
            limit: Maximum number of jobs to return
            min_combined_score: Minimum combined score threshold
            
        Returns:
            List of top matching jobs, sorted by combined score
        """
        try:
            # Filter jobs by minimum score
            qualified_jobs = [
                job for job in jobs 
                if job.combined_match_score and job.combined_match_score >= min_combined_score
            ]
            
            # Sort by combined score (descending)
            sorted_jobs = sorted(
                qualified_jobs,
                key=lambda x: x.combined_match_score or 0,
                reverse=True
            )
            
            return sorted_jobs[:limit]
            
        except Exception as e:
            logger.error(f"Error getting top matches: {e}")
            return jobs[:limit]  # Return first jobs as fallback
    
    async def semantic_job_search(self, search_query: str, user_profile: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[JobPosting]:
        """
        Perform semantic job search across stored jobs.
        
        Args:
            search_query: Natural language search query
            user_profile: User profile for personalized matching
            limit: Maximum number of results to return
            
        Returns:
            List of semantically matched jobs
        """
        try:
            # Get jobs with embeddings from database
            all_jobs = database_service.get_jobs_with_embeddings(limit=100)  # Get more jobs to search through
            
            if not all_jobs:
                logger.warning("No jobs with embeddings found in database for semantic search")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_service.encode_text(search_query)
            
            # Calculate similarities for jobs with embeddings
            similarities = []
            for job in all_jobs:
                if job.description_embedding:
                    job_embedding = self.embedding_service.embedding_from_json(job.description_embedding)
                    similarity = self.embedding_service.calculate_similarity(query_embedding, job_embedding)
                    similarities.append((job, similarity))
                else:
                    # This shouldn't happen since we're getting jobs with embeddings
                    similarities.append((job, 0.0))
            
            # Sort by similarity and return top matches
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Create result jobs with similarity scores for display
            top_jobs = []
            for job, similarity in similarities[:limit]:
                # Update the job object with the similarity score for display
                job.semantic_similarity_score = similarity
                top_jobs.append(job)
            
            logger.info(f"Semantic search for '{search_query}' returned {len(top_jobs)} results")
            return top_jobs
            
        except Exception as e:
            logger.error(f"Error in semantic job search: {e}")
            return []
    
    def get_analysis_stats(self, jobs: List[JobPosting]) -> Dict[str, Any]:
        """
        Get statistics about semantic analysis results.
        
        Args:
            jobs: List of analyzed JobPosting instances
            
        Returns:
            Dictionary with analysis statistics
        """
        try:
            total_jobs = len(jobs)
            jobs_with_embeddings = sum(1 for job in jobs if job.description_embedding)
            jobs_with_semantic_scores = sum(1 for job in jobs if job.semantic_similarity_score is not None)
            jobs_with_combined_scores = sum(1 for job in jobs if job.combined_match_score is not None)
            
            # Score distributions
            semantic_scores = [job.semantic_similarity_score for job in jobs if job.semantic_similarity_score is not None]
            combined_scores = [job.combined_match_score for job in jobs if job.combined_match_score is not None]
            
            stats = {
                "total_jobs": total_jobs,
                "jobs_with_embeddings": jobs_with_embeddings,
                "jobs_with_semantic_scores": jobs_with_semantic_scores,
                "jobs_with_combined_scores": jobs_with_combined_scores,
                "embedding_coverage": jobs_with_embeddings / total_jobs if total_jobs > 0 else 0,
                "semantic_analysis_coverage": jobs_with_semantic_scores / total_jobs if total_jobs > 0 else 0,
            }
            
            if semantic_scores:
                stats.update({
                    "avg_semantic_similarity": sum(semantic_scores) / len(semantic_scores),
                    "max_semantic_similarity": max(semantic_scores),
                    "min_semantic_similarity": min(semantic_scores)
                })
            
            if combined_scores:
                stats.update({
                    "avg_combined_score": sum(combined_scores) / len(combined_scores),
                    "max_combined_score": max(combined_scores),
                    "min_combined_score": min(combined_scores)
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating analysis stats: {e}")
            return {"error": str(e)}

# Global instance for easy access
_semantic_analysis_service = None

def get_semantic_analysis_service(embedding_model: str = 'all-MiniLM-L6-v2') -> SemanticAnalysisService:
    """
    Get or create the global semantic analysis service instance.
    
    Args:
        embedding_model: Name of the embedding model to use
        
    Returns:
        SemanticAnalysisService instance
    """
    global _semantic_analysis_service
    if _semantic_analysis_service is None:
        _semantic_analysis_service = SemanticAnalysisService(embedding_model)
    return _semantic_analysis_service 