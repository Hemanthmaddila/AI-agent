"""
Scraper Manager - Orchestrates multiple job site scrapers
Handles deduplication, parallel execution, and unified results
"""
import asyncio
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import time
from urllib.parse import urlparse
import hashlib

from .base_scraper import JobScraper, ScraperResult, ScraperConfig
from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

@dataclass
class MultiSiteSearchResult:
    """Aggregated results from multiple scrapers"""
    all_jobs: List[JobPosting]
    results_by_source: Dict[str, ScraperResult]
    total_found: int
    successful_sources: List[str]
    failed_sources: List[str]
    execution_time: float
    duplicates_removed: int

class ScraperManager:
    """
    Manages multiple job scrapers and provides unified job discovery.
    Handles parallel execution, deduplication, and result aggregation.
    """
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.scrapers: Dict[str, JobScraper] = {}
        self.enabled_sources: Set[str] = set()
        
    def register_scraper(self, scraper: JobScraper, enabled: bool = True):
        """Register a job scraper"""
        source_name = scraper.site_name.lower()
        self.scrapers[source_name] = scraper
        
        if enabled:
            self.enabled_sources.add(source_name)
            
        logger.info(f"Registered scraper for {scraper.site_name} (enabled: {enabled})")
    
    def enable_source(self, source_name: str):
        """Enable a specific job source"""
        if source_name.lower() in self.scrapers:
            self.enabled_sources.add(source_name.lower())
            logger.info(f"Enabled source: {source_name}")
        else:
            logger.warning(f"Source not found: {source_name}")
    
    def disable_source(self, source_name: str):
        """Disable a specific job source"""
        self.enabled_sources.discard(source_name.lower())
        logger.info(f"Disabled source: {source_name}")
    
    def get_available_sources(self) -> List[str]:
        """Get list of available job sources"""
        return list(self.scrapers.keys())
    
    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled job sources"""
        return list(self.enabled_sources)
    
    async def search_all_sources(
        self, 
        keywords: str, 
        location: Optional[str] = None, 
        num_results_per_source: int = 10,
        sources: Optional[List[str]] = None
    ) -> MultiSiteSearchResult:
        """
        Search for jobs across all enabled sources or specified sources.
        
        Args:
            keywords: Job search keywords
            location: Location filter (optional)
            num_results_per_source: Max results per source
            sources: Specific sources to search (if None, uses all enabled)
            
        Returns:
            MultiSiteSearchResult with aggregated data
        """
        start_time = time.time()
        
        # Determine which sources to search
        target_sources = sources or list(self.enabled_sources)
        target_sources = [s.lower() for s in target_sources if s.lower() in self.scrapers]
        
        if not target_sources:
            logger.warning("No valid sources specified or enabled")
            return MultiSiteSearchResult(
                all_jobs=[],
                results_by_source={},
                total_found=0,
                successful_sources=[],
                failed_sources=[],
                execution_time=time.time() - start_time,
                duplicates_removed=0
            )
        
        logger.info(f"Starting search across {len(target_sources)} sources: {target_sources}")
        
        # Create search tasks for parallel execution
        search_tasks = []
        for source_name in target_sources:
            scraper = self.scrapers[source_name]
            task = asyncio.create_task(
                self._search_with_error_handling(
                    scraper, keywords, location, num_results_per_source
                )
            )
            search_tasks.append((source_name, task))
        
        # Execute all searches in parallel
        results_by_source = {}
        for source_name, task in search_tasks:
            try:
                result = await task
                results_by_source[source_name] = result
            except Exception as e:
                logger.error(f"Critical error in {source_name} scraper: {e}")
                results_by_source[source_name] = ScraperResult(
                    jobs=[],
                    source=source_name,
                    success=False,
                    error_message=str(e)
                )
        
        # Aggregate results
        all_jobs = []
        successful_sources = []
        failed_sources = []
        
        for source_name, result in results_by_source.items():
            if result.success:
                all_jobs.extend(result.jobs)
                successful_sources.append(source_name)
            else:
                failed_sources.append(source_name)
        
        # Remove duplicates
        deduplicated_jobs, duplicates_removed = self._deduplicate_jobs(all_jobs)
        
        execution_time = time.time() - start_time
        
        logger.info(
            f"Search completed: {len(deduplicated_jobs)} unique jobs found "
            f"({duplicates_removed} duplicates removed) "
            f"in {execution_time:.2f}s"
        )
        
        return MultiSiteSearchResult(
            all_jobs=deduplicated_jobs,
            results_by_source=results_by_source,
            total_found=len(deduplicated_jobs),
            successful_sources=successful_sources,
            failed_sources=failed_sources,
            execution_time=execution_time,
            duplicates_removed=duplicates_removed
        )
    
    async def _search_with_error_handling(
        self, 
        scraper: JobScraper, 
        keywords: str, 
        location: Optional[str], 
        num_results: int
    ) -> ScraperResult:
        """Execute search with comprehensive error handling"""
        try:
            logger.info(f"Starting search on {scraper.site_name}")
            result = await scraper.search_jobs(keywords, location, num_results)
            
            if result.success:
                logger.info(f"{scraper.site_name}: Found {len(result.jobs)} jobs")
            else:
                logger.warning(f"{scraper.site_name}: Search failed - {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching {scraper.site_name}: {e}")
            return ScraperResult(
                jobs=[],
                source=scraper.site_name,
                success=False,
                error_message=f"Scraper exception: {str(e)}"
            )
        finally:
            # Ensure cleanup happens
            try:
                await scraper.cleanup()
            except Exception as e:
                logger.warning(f"Cleanup error for {scraper.site_name}: {e}")
    
    def _deduplicate_jobs(self, jobs: List[JobPosting]) -> tuple[List[JobPosting], int]:
        """
        Remove duplicate job postings based on multiple criteria.
        
        Args:
            jobs: List of job postings to deduplicate
            
        Returns:
            Tuple of (deduplicated_jobs, number_of_duplicates_removed)
        """
        if not jobs:
            return [], 0
        
        unique_jobs = []
        seen_signatures = set()
        duplicates_count = 0
        
        for job in jobs:
            # Create multiple signatures for duplicate detection
            signatures = self._generate_job_signatures(job)
            
            # Check if any signature has been seen before
            is_duplicate = any(sig in seen_signatures for sig in signatures)
            
            if not is_duplicate:
                unique_jobs.append(job)
                # Add all signatures to seen set
                seen_signatures.update(signatures)
            else:
                duplicates_count += 1
                logger.debug(f"Duplicate found: {job.title} at {job.company_name}")
        
        return unique_jobs, duplicates_count
    
    def _generate_job_signatures(self, job: JobPosting) -> List[str]:
        """
        Generate multiple signatures for a job to detect duplicates.
        Uses different combinations of job attributes.
        """
        signatures = []
        
        # Signature 1: URL-based (most reliable)
        if job.job_url:
            normalized_url = self._normalize_url(job.job_url)
            signatures.append(f"url:{normalized_url}")
        
        # Signature 2: Title + Company combination
        if job.title and job.company_name:
            title_company = f"{job.title.lower().strip()}|{job.company_name.lower().strip()}"
            title_company_hash = hashlib.md5(title_company.encode()).hexdigest()
            signatures.append(f"title_company:{title_company_hash}")
        
        # Signature 3: Content-based (description snippet)
        if job.full_description_raw and len(job.full_description_raw) > 100:
            # Use first 200 characters of description
            desc_snippet = job.full_description_raw[:200].lower().strip()
            desc_hash = hashlib.md5(desc_snippet.encode()).hexdigest()
            signatures.append(f"content:{desc_hash}")
        
        return signatures
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URLs for comparison"""
        try:
            parsed = urlparse(url)
            # Remove query parameters and fragments for comparison
            normalized = f"{parsed.netloc}{parsed.path}".lower()
            return normalized
        except Exception:
            return url.lower()
    
    async def cleanup_all(self):
        """Clean up all registered scrapers"""
        cleanup_tasks = []
        for scraper in self.scrapers.values():
            cleanup_tasks.append(scraper.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            logger.info("All scrapers cleaned up")
    
    def get_source_statistics(self) -> Dict[str, Dict[str, any]]:
        """Get statistics about available sources"""
        stats = {}
        for source_name, scraper in self.scrapers.items():
            stats[source_name] = {
                'site_name': scraper.site_name,
                'base_url': scraper.base_url,
                'enabled': source_name in self.enabled_sources,
                'class_name': scraper.__class__.__name__
            }
        return stats 