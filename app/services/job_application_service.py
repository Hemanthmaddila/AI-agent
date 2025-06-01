"""
Job Application Automation Service - Multi-platform job application automation
"""
import asyncio
import logging
import json
import time
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from app.models.job_posting_models import JobPosting
from config.enhanced_settings import enhanced_settings

# Import platform scrapers
from app.services.scrapers.indeed_scraper import IndeedScraper
from app.services.scrapers.linkedin_scraper import LinkedInScraper
from app.services.scrapers.remote_co_scraper import RemoteCoScraper
from app.services.web_browser_service import web_browser_service

# Import the browser automation service
try:
    from app.services.browser_automation_service import browser_service
    BROWSER_SERVICE_AVAILABLE = True
except ImportError:
    BROWSER_SERVICE_AVAILABLE = False
    browser_service = None

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """User profile for job applications"""
    name: str
    email: str
    phone: str
    linkedin: str = ""
    github: str = ""
    website: str = ""
    location: str = ""
    resume_path: str = ""
    cover_letter_template: str = ""
    years_experience: int = 0
    salary_expectation: str = ""
    availability: str = "Immediately"
    
    # Skills and preferences
    skills: List[str] = field(default_factory=list)
    preferred_locations: List[str] = field(default_factory=list)
    job_types: List[str] = field(default_factory=lambda: ["Full-time", "Remote"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for form filling"""
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'linkedin': self.linkedin,
            'github': self.github,
            'website': self.website,
            'location': self.location,
            'resume_path': self.resume_path,
            'cover_letter': self.cover_letter_template,
            'experience': str(self.years_experience),
            'salary': self.salary_expectation,
            'availability': self.availability
        }

@dataclass
class ApplicationResult:
    """Result of a job application attempt"""
    job_id: int
    job_title: str
    company_name: str
    platform: str
    success: bool
    application_date: datetime
    error_message: Optional[str] = None
    application_url: Optional[str] = None
    notes: str = ""

class JobApplicationService:
    """Comprehensive job application automation across multiple platforms"""
    
    def __init__(self):
        self.profile: Optional[UserProfile] = None
        self.application_history: List[ApplicationResult] = []
        self.current_task_id = None
        
        # Initialize platform scrapers
        self.scrapers = {
            'indeed': IndeedScraper(),
            'linkedin': LinkedInScraper(),
            'remote.co': RemoteCoScraper()
        }
        
        # Load user profile if exists
        self._load_user_profile()
    
    async def _update_progress(self, message: str, progress: float):
        """Update task progress if browser service is available"""
        if BROWSER_SERVICE_AVAILABLE and browser_service and self.current_task_id:
            await browser_service.update_task_progress(self.current_task_id, message, progress)
        logger.info(f"🤖 JobApplication: {message} ({progress}%)")
    
    def _load_user_profile(self):
        """Load user profile from file"""
        try:
            profile_path = Path("data/user_profiles/default_profile.json")
            if profile_path.exists():
                with open(profile_path, 'r') as f:
                    data = json.load(f)
                    self.profile = UserProfile(**data)
                logger.info("✅ User profile loaded successfully")
            else:
                logger.info("No user profile found - will need to create one")
        except Exception as e:
            logger.warning(f"Error loading user profile: {e}")
    
    def save_user_profile(self, profile: UserProfile):
        """Save user profile to file"""
        try:
            profile_dir = Path("data/user_profiles")
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            profile_path = profile_dir / "default_profile.json"
            with open(profile_path, 'w') as f:
                json.dump(profile.__dict__, f, indent=2)
            
            self.profile = profile
            logger.info("✅ User profile saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")
    
    def create_profile_interactive(self) -> UserProfile:
        """Create user profile through interactive prompts"""
        print("\n" + "="*60)
        print("🤖 JOB APPLICATION PROFILE SETUP")
        print("="*60)
        print("Let's set up your profile for automated job applications.")
        print("You can update this information anytime.\n")
        
        name = input("Full Name: ").strip()
        email = input("Email Address: ").strip()
        phone = input("Phone Number: ").strip()
        linkedin = input("LinkedIn Profile URL (optional): ").strip()
        github = input("GitHub Profile URL (optional): ").strip()
        website = input("Personal Website (optional): ").strip()
        location = input("Current Location: ").strip()
        
        # Resume file
        resume_path = input("Resume File Path (optional): ").strip()
        if resume_path and not Path(resume_path).exists():
            print("⚠️ Resume file not found. You can update this later.")
            resume_path = ""
        
        # Cover letter template
        print("\nCover Letter Template (optional):")
        print("Enter a brief template that can be customized for each application:")
        cover_letter = input().strip()
        
        try:
            years_experience = int(input("Years of Experience: ").strip() or "0")
        except ValueError:
            years_experience = 0
        
        salary_expectation = input("Salary Expectation (optional): ").strip()
        availability = input("Availability (default: Immediately): ").strip() or "Immediately"
        
        # Skills
        print("\nSkills (comma-separated):")
        skills_input = input().strip()
        skills = [skill.strip() for skill in skills_input.split(',') if skill.strip()]
        
        # Preferred locations
        print("\nPreferred Job Locations (comma-separated):")
        locations_input = input().strip()
        preferred_locations = [loc.strip() for loc in locations_input.split(',') if loc.strip()]
        
        profile = UserProfile(
            name=name,
            email=email,
            phone=phone,
            linkedin=linkedin,
            github=github,
            website=website,
            location=location,
            resume_path=resume_path,
            cover_letter_template=cover_letter,
            years_experience=years_experience,
            salary_expectation=salary_expectation,
            availability=availability,
            skills=skills,
            preferred_locations=preferred_locations
        )
        
        # Save the profile
        self.save_user_profile(profile)
        
        print("\n✅ Profile created successfully!")
        return profile
    
    async def apply_to_job_by_id(self, job_id: int) -> ApplicationResult:
        """Apply to a specific job by its database ID"""
        try:
            # Get job from database
            from app.services.database_service import database_service
            
            job = await database_service.get_job_by_id(job_id)
            if not job:
                return ApplicationResult(
                    job_id=job_id,
                    job_title="Unknown",
                    company_name="Unknown",
                    platform="Unknown",
                    success=False,
                    application_date=datetime.now(),
                    error_message="Job not found in database"
                )
            
            return await self.apply_to_job(job)
            
        except Exception as e:
            logger.error(f"Error applying to job {job_id}: {e}")
            return ApplicationResult(
                job_id=job_id,
                job_title="Unknown",
                company_name="Unknown",
                platform="Unknown",
                success=False,
                application_date=datetime.now(),
                error_message=str(e)
            )
    
    async def apply_to_job(self, job: JobPosting) -> ApplicationResult:
        """Apply to a specific job"""
        try:
            if not self.profile:
                error_msg = "User profile not set up. Please create a profile first."
                logger.error(error_msg)
                return ApplicationResult(
                    job_id=job.id or 0,
                    job_title=job.title,
                    company_name=job.company_name,
                    platform=job.source_platform,
                    success=False,
                    application_date=datetime.now(),
                    error_message=error_msg
                )
            
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"Apply to {job.title} at {job.company_name}",
                    [
                        "Validate job details",
                        "Navigate to application",
                        "Fill application form",
                        "Submit application"
                    ]
                )
            
            await self._update_progress(f"Starting application to {job.title}", 10)
            
            # Determine platform and use appropriate scraper
            platform = job.source_platform.lower()
            
            if 'linkedin' in platform:
                success = await self._apply_via_linkedin(job)
            elif 'indeed' in platform:
                success = await self._apply_via_indeed(job)
            elif 'remote' in platform:
                success = await self._apply_via_remote_co(job)
            else:
                # Generic career portal application
                success = await self._apply_via_generic_portal(job)
            
            # Record application result
            result = ApplicationResult(
                job_id=job.id or 0,
                job_title=job.title,
                company_name=job.company_name,
                platform=job.source_platform,
                success=success,
                application_date=datetime.now(),
                application_url=job.job_url,
                notes=f"Applied via {platform}"
            )
            
            self.application_history.append(result)
            await self._save_application_result(result)
            
            if success:
                await self._update_progress("Application submitted successfully!", 100)
            else:
                await self._update_progress("Application failed", 100)
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying to job: {e}")
            result = ApplicationResult(
                job_id=job.id or 0,
                job_title=job.title,
                company_name=job.company_name,
                platform=job.source_platform,
                success=False,
                application_date=datetime.now(),
                error_message=str(e)
            )
            self.application_history.append(result)
            return result
    
    async def _apply_via_linkedin(self, job: JobPosting) -> bool:
        """Apply to job via LinkedIn"""
        try:
            await self._update_progress("Applying via LinkedIn", 30)
            
            linkedin_scraper = self.scrapers['linkedin']
            
            # Get browser page
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                if not browser_service.browser:
                    await browser_service.start_browser()
                page = browser_service.page
            else:
                # Fallback: create browser
                from playwright.async_api import async_playwright
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(headless=False)
                context = await browser.new_context()
                page = await context.new_page()
            
            # Use LinkedIn scraper's apply method
            success = await linkedin_scraper.apply_to_job(job.job_url, page, self.profile.to_dict())
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying via LinkedIn: {e}")
            return False
    
    async def _apply_via_indeed(self, job: JobPosting) -> bool:
        """Apply to job via Indeed"""
        try:
            await self._update_progress("Applying via Indeed", 30)
            
            # Indeed typically redirects to external sites
            # Use generic portal method
            return await self._apply_via_generic_portal(job)
            
        except Exception as e:
            logger.error(f"Error applying via Indeed: {e}")
            return False
    
    async def _apply_via_remote_co(self, job: JobPosting) -> bool:
        """Apply to job via Remote.co"""
        try:
            await self._update_progress("Applying via Remote.co", 30)
            
            # Remote.co typically links to external applications
            return await self._apply_via_generic_portal(job)
            
        except Exception as e:
            logger.error(f"Error applying via Remote.co: {e}")
            return False
    
    async def _apply_via_generic_portal(self, job: JobPosting) -> bool:
        """Apply to job via generic career portal"""
        try:
            await self._update_progress("Applying via generic career portal", 30)
            
            # Use web browser service for generic applications
            success = await web_browser_service.apply_to_career_portal_job(
                job.job_url, 
                self.profile.to_dict()
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error applying via generic portal: {e}")
            return False
    
    async def _save_application_result(self, result: ApplicationResult):
        """Save application result to database"""
        try:
            from app.services.database_service import database_service
            
            # Update job status in database
            await database_service.update_job_application_status(
                result.job_id,
                "applied" if result.success else "application_failed",
                {
                    'application_date': result.application_date.isoformat(),
                    'application_url': result.application_url,
                    'notes': result.notes,
                    'error_message': result.error_message
                }
            )
            
        except Exception as e:
            logger.error(f"Error saving application result: {e}")
    
    async def bulk_apply_to_jobs(self, job_ids: List[int], max_applications: int = 10) -> List[ApplicationResult]:
        """Apply to multiple jobs in batch"""
        results = []
        
        try:
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"Bulk Application: {len(job_ids)} jobs",
                    [
                        "Initialize applications",
                        "Apply to jobs",
                        "Process results",
                        "Generate report"
                    ]
                )
            
            await self._update_progress(f"Starting bulk application to {len(job_ids)} jobs", 10)
            
            applied_count = 0
            
            for i, job_id in enumerate(job_ids):
                if applied_count >= max_applications:
                    logger.info(f"Reached maximum applications limit: {max_applications}")
                    break
                
                try:
                    progress = 20 + (i / len(job_ids)) * 70
                    await self._update_progress(f"Applying to job {i+1}/{len(job_ids)}", progress)
                    
                    result = await self.apply_to_job_by_id(job_id)
                    results.append(result)
                    
                    if result.success:
                        applied_count += 1
                        logger.info(f"✅ Successfully applied to {result.job_title}")
                    else:
                        logger.warning(f"❌ Failed to apply to {result.job_title}: {result.error_message}")
                    
                    # Add delay between applications
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error applying to job {job_id}: {e}")
                    continue
            
            await self._update_progress(f"Completed bulk application: {applied_count} successful", 100)
            
        except Exception as e:
            logger.error(f"Error in bulk apply: {e}")
        
        return results
    
    async def smart_job_discovery_and_apply(self, keywords: str, max_applications: int = 5) -> Dict[str, Any]:
        """Discover jobs across all platforms and apply to the best matches"""
        results = {
            'keywords': keywords,
            'jobs_discovered': 0,
            'applications_submitted': 0,
            'platforms_searched': [],
            'applications': [],
            'errors': []
        }
        
        try:
            if BROWSER_SERVICE_AVAILABLE and browser_service:
                self.current_task_id = await browser_service.create_task(
                    f"Smart Job Discovery & Apply: {keywords}",
                    [
                        "Search all platforms",
                        "Analyze job matches",
                        "Apply to best matches",
                        "Generate report"
                    ]
                )
            
            await self._update_progress("Starting smart job discovery", 10)
            
            # Step 1: Search all platforms
            all_jobs = []
            
            for platform_name, scraper in self.scrapers.items():
                try:
                    await self._update_progress(f"Searching {platform_name}", 20)
                    
                    scraper_result = await scraper.search_jobs(keywords, num_results=10)
                    if scraper_result.success:
                        all_jobs.extend(scraper_result.jobs)
                        results['platforms_searched'].append(platform_name)
                        logger.info(f"Found {len(scraper_result.jobs)} jobs on {platform_name}")
                    
                except Exception as e:
                    results['errors'].append(f"Error searching {platform_name}: {str(e)}")
                    continue
            
            results['jobs_discovered'] = len(all_jobs)
            
            if not all_jobs:
                results['errors'].append("No jobs found on any platform")
                return results
            
            # Step 2: Analyze and rank jobs
            await self._update_progress("Analyzing job matches", 50)
            
            # Simple ranking based on title keywords for now
            # Can be enhanced with AI-powered matching
            ranked_jobs = self._rank_jobs_by_relevance(all_jobs, keywords)
            
            # Step 3: Apply to top matches
            await self._update_progress("Applying to top job matches", 60)
            
            applied_count = 0
            for job in ranked_jobs[:max_applications]:
                try:
                    result = await self.apply_to_job(job)
                    results['applications'].append({
                        'title': result.job_title,
                        'company': result.company_name,
                        'platform': result.platform,
                        'success': result.success,
                        'error': result.error_message
                    })
                    
                    if result.success:
                        applied_count += 1
                    
                except Exception as e:
                    results['errors'].append(f"Error applying to {job.title}: {str(e)}")
                    continue
            
            results['applications_submitted'] = applied_count
            
            await self._update_progress(f"Smart discovery complete: {applied_count} applications", 100)
            
        except Exception as e:
            results['errors'].append(f"Workflow error: {str(e)}")
        
        return results
    
    def _rank_jobs_by_relevance(self, jobs: List[JobPosting], keywords: str) -> List[JobPosting]:
        """Rank jobs by relevance to keywords"""
        try:
            keyword_list = keywords.lower().split()
            
            def calculate_relevance(job: JobPosting) -> float:
                score = 0
                title_lower = job.title.lower()
                desc_lower = job.full_description_raw.lower()
                
                # Title keywords get higher weight
                for keyword in keyword_list:
                    if keyword in title_lower:
                        score += 10
                    if keyword in desc_lower:
                        score += 2
                
                return score
            
            # Sort by relevance score
            return sorted(jobs, key=calculate_relevance, reverse=True)
            
        except Exception as e:
            logger.error(f"Error ranking jobs: {e}")
            return jobs
    
    def get_application_summary(self) -> Dict[str, Any]:
        """Get summary of application history"""
        total_apps = len(self.application_history)
        successful_apps = sum(1 for app in self.application_history if app.success)
        
        platforms = {}
        for app in self.application_history:
            platform = app.platform
            if platform not in platforms:
                platforms[platform] = {'total': 0, 'successful': 0}
            platforms[platform]['total'] += 1
            if app.success:
                platforms[platform]['successful'] += 1
        
        recent_apps = sorted(
            self.application_history, 
            key=lambda x: x.application_date, 
            reverse=True
        )[:10]
        
        return {
            'total_applications': total_apps,
            'successful_applications': successful_apps,
            'success_rate': (successful_apps / total_apps * 100) if total_apps > 0 else 0,
            'platforms': platforms,
            'recent_applications': [
                {
                    'title': app.job_title,
                    'company': app.company_name,
                    'platform': app.platform,
                    'success': app.success,
                    'date': app.application_date.strftime('%Y-%m-%d %H:%M')
                }
                for app in recent_apps
            ]
        }
    
    async def close(self):
        """Clean up resources"""
        try:
            for scraper in self.scrapers.values():
                if hasattr(scraper, 'close'):
                    await scraper.close()
        except Exception as e:
            logger.error(f"Error closing job application service: {e}")

# Global instance
job_application_service = JobApplicationService() 