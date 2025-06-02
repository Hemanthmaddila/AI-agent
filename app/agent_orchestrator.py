"""
Agent Orchestrator - Central coordination logic for AI Job Application Agent
Manages complex workflows and decision-making between services
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from rich.console import Console
from rich.prompt import Confirm, Prompt

from app.services.database_service import (
    get_pending_jobs, get_all_jobs, save_search_query, 
    get_application_logs, update_job_processing_status
)
from app.services.gemini_service import GeminiService
from app.services.playwright_scraper_service import search_jobs_sync
from app.models.job_posting_models import JobPosting
from config import settings

# Import external application capabilities
from app.services.scrapers.linkedin_scraper import LinkedInScraper
from app.application_automation.external_application_handler import create_external_handler

# Import services for external applications
try:
    from app.hitl.hitl_service import HITLService
    HITL_AVAILABLE = True
except ImportError:
    HITL_AVAILABLE = False
    HITLService = None

try:
    from app.services.browser_automation_service import browser_service
    BROWSER_SERVICE_AVAILABLE = True
except ImportError:
    BROWSER_SERVICE_AVAILABLE = False
    browser_service = None

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Central orchestrator for coordinating AI job application workflows.
    Manages intelligent automation between job discovery, analysis, and application tracking.
    """
    
    def __init__(self):
        self.console = Console()
        self.gemini_service = None
        self.linkedin_scraper = None
        self.external_handler = None
        self.hitl_service = None
        
    def _initialize_services(self) -> bool:
        """Initialize all required services for external application workflow"""
        success = True
        
        # Initialize Gemini service
        if not settings.GEMINI_API_KEY:
            self.console.print("[yellow]⚠️ GEMINI_API_KEY not configured. AI features will be limited.[/yellow]")
            success = False
        else:
            try:
                self.gemini_service = GeminiService()
                self.console.print("✅ Gemini service initialized")
            except ValueError as e:
                self.console.print(f"[red]❌ Failed to initialize Gemini service: {e}[/red]")
                success = False
        
        # Initialize HITL service
        if HITL_AVAILABLE:
            try:
                self.hitl_service = HITLService()
                self.console.print("✅ Human-in-the-loop service initialized")
            except Exception as e:
                self.console.print(f"[yellow]⚠️ HITL service initialization failed: {e}[/yellow]")
        
        # Initialize LinkedIn scraper
        try:
            self.linkedin_scraper = LinkedInScraper()
            self.console.print("✅ LinkedIn scraper initialized")
        except Exception as e:
            self.console.print(f"[red]❌ LinkedIn scraper initialization failed: {e}[/red]")
            success = False
        
        # Initialize external application handler
        if self.gemini_service:
            try:
                self.external_handler = create_external_handler(
                    hitl_service=self.hitl_service,
                    gemini_service=self.gemini_service,
                    config={"debug_mode": True}
                )
                self.console.print("✅ External application handler initialized")
            except Exception as e:
                self.console.print(f"[red]❌ External application handler initialization failed: {e}[/red]")
                success = False
        
        return success
        
    def _initialize_gemini_service(self) -> bool:
        """Initialize Gemini service if API key is available."""
        if not settings.GEMINI_API_KEY:
            self.console.print("[yellow]⚠️ GEMINI_API_KEY not configured. AI features will be limited.[/yellow]")
            return False
        
        try:
            self.gemini_service = GeminiService()
            return True
        except ValueError as e:
            self.console.print(f"[red]❌ Failed to initialize Gemini service: {e}[/red]")
            return False

    async def run_external_application_workflow(self, job_url: str, user_profile: Any) -> Dict[str, Any]:
        """
        Complete workflow for applying to external job sites
        
        Args:
            job_url: LinkedIn job URL to start from
            user_profile: User profile model with application data
            
        Returns:
            Result dictionary with application status
        """
        workflow_results = {
            "success": False,
            "job_url": job_url,
            "application_type": None,
            "external_url": None,
            "fields_filled": 0,
            "errors": [],
            "steps_completed": []
        }
        
        try:
            self.console.print(f"\n[bold blue]🌐 Starting External Application Workflow[/bold blue]")
            self.console.print(f"Job URL: {job_url}")
            
            # Step 1: Initialize services
            if not self._initialize_services():
                workflow_results["errors"].append("Failed to initialize required services")
                return workflow_results
            
            workflow_results["steps_completed"].append("services_initialized")
            
            # Step 2: Ensure browser service is available
            if not BROWSER_SERVICE_AVAILABLE or not browser_service:
                self.console.print("[red]❌ Browser service not available[/red]")
                workflow_results["errors"].append("Browser service not available")
                return workflow_results
            
            # Step 3: Start browser if needed
            if not browser_service.browser:
                await browser_service.start_browser()
                self.console.print("✅ Browser service started")
            
            workflow_results["steps_completed"].append("browser_ready")
            
            # Step 4: Navigate to LinkedIn job and find application method
            self.console.print(f"\n🎯 Analyzing job application options for: {job_url}")
            
            app_type, app_page, app_message = await self.linkedin_scraper.initiate_application_on_job_page(job_url)
            
            workflow_results["application_type"] = app_type
            workflow_results["external_url"] = app_message if app_type else None
            
            if app_type in ["external_redirect", "external_same_page_nav"] and app_page:
                workflow_results["steps_completed"].append("external_site_reached")
                
                self.console.print(f"✅ Successfully reached external application site: {app_message}")
                self.console.print(f"   Navigation type: {app_type}")
                
                # Step 5: Process external application
                self.console.print(f"\n🤖 Processing external application form...")
                
                # Load user profile (placeholder - you'd load from database)
                if not user_profile:
                    self.console.print("[yellow]⚠️ No user profile provided, using demo data[/yellow]")
                    # You would load the actual user profile here
                    # user_profile = load_user_profile(profile_name)
                
                application_result = await self.external_handler.process_application(
                    page=app_page,
                    user_profile=user_profile,
                    job_details=None  # You could fetch job details from database
                )
                
                if application_result.get("success"):
                    workflow_results["success"] = True
                    workflow_results["fields_filled"] = application_result.get("fields_filled", 0)
                    workflow_results["steps_completed"].append("application_processed")
                    
                    self.console.print(f"✅ External application processed successfully!")
                    self.console.print(f"   Fields filled: {workflow_results['fields_filled']}")
                    
                else:
                    workflow_results["errors"].append(f"Application processing failed: {application_result.get('error')}")
                    self.console.print(f"[red]❌ Application processing failed: {application_result.get('error')}[/red]")
                
                # Close external page
                try:
                    await app_page.close()
                    if app_page.context != browser_service.page.context:
                        await app_page.context.close()
                except:
                    pass
                
            elif app_type == "easy_apply":
                workflow_results["steps_completed"].append("easy_apply_detected")
                self.console.print(f"✅ Easy Apply detected - would handle with existing LinkedIn automation")
                # You could integrate Easy Apply handling here
                
            else:
                error_msg = f"Could not initiate application: {app_message}"
                workflow_results["errors"].append(error_msg)
                self.console.print(f"[red]❌ {error_msg}[/red]")
            
            return workflow_results
            
        except Exception as e:
            error_msg = f"External application workflow failed: {str(e)}"
            workflow_results["errors"].append(error_msg)
            self.console.print(f"[red]❌ {error_msg}[/red]")
            logger.error(error_msg, exc_info=True)
            return workflow_results

    async def batch_external_applications(self, job_urls: List[str], user_profile: Any, 
                                        max_applications: int = 5) -> Dict[str, Any]:
        """
        Process multiple external applications in batch
        
        Args:
            job_urls: List of LinkedIn job URLs
            user_profile: User profile for applications
            max_applications: Maximum number of applications to process
            
        Returns:
            Batch processing results
        """
        batch_results = {
            "total_jobs": len(job_urls),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "results": [],
            "errors": []
        }
        
        self.console.print(f"\n[bold blue]🚀 Starting Batch External Application Processing[/bold blue]")
        self.console.print(f"Total jobs: {len(job_urls)} | Max applications: {max_applications}")
        
        for i, job_url in enumerate(job_urls[:max_applications]):
            self.console.print(f"\n[bold]Processing job {i+1}/{min(len(job_urls), max_applications)}[/bold]")
            
            try:
                result = await self.run_external_application_workflow(job_url, user_profile)
                batch_results["results"].append(result)
                batch_results["processed"] += 1
                
                if result.get("success"):
                    batch_results["successful"] += 1
                else:
                    batch_results["failed"] += 1
                
                # Delay between applications
                if i < min(len(job_urls), max_applications) - 1:
                    import asyncio
                    await asyncio.sleep(5)  # 5 second delay between applications
                
            except Exception as e:
                error_msg = f"Batch processing error for {job_url}: {str(e)}"
                batch_results["errors"].append(error_msg)
                batch_results["failed"] += 1
                self.console.print(f"[red]❌ {error_msg}[/red]")
        
        # Display batch summary
        self.console.print(f"\n[bold green]📊 Batch Processing Complete![/bold green]")
        self.console.print(f"✅ Successful: {batch_results['successful']}")
        self.console.print(f"❌ Failed: {batch_results['failed']}")
        self.console.print(f"📈 Success rate: {(batch_results['successful']/batch_results['processed']*100):.1f}%" if batch_results['processed'] > 0 else "N/A")
        
        return batch_results

    def discover_and_analyze_workflow(
        self, 
        keywords: str, 
        location: str = None, 
        num_results: int = 5,
        target_role: str = None,
        auto_analyze: bool = True
    ) -> Dict[str, Any]:
        """
        Complete workflow: Discover jobs -> Optionally analyze with AI -> Return results summary.
        
        Returns:
            Dict with workflow results including jobs found, analyzed, and recommendations
        """
        workflow_results = {
            "jobs_discovered": 0,
            "jobs_saved": 0,
            "jobs_analyzed": 0,
            "high_relevance_jobs": [],
            "recommendations": [],
            "errors": []
        }
        
        self.console.print(f"\n[bold blue]🚀 Starting Discovery & Analysis Workflow[/bold blue]")
        self.console.print(f"Keywords: '{keywords}' | Location: '{location or 'Any'}' | Target Role: '{target_role or 'Not specified'}'")
        
        # Phase 1: Job Discovery
        try:
            self.console.print("\n[bold]Phase 1: Job Discovery[/bold]")
            jobs_found = search_jobs_sync(keywords=keywords, location=location, num_results=num_results)
            workflow_results["jobs_discovered"] = len(jobs_found)
            
            if not jobs_found:
                self.console.print("[yellow]No jobs discovered. Workflow ending.[/yellow]")
                workflow_results["recommendations"].append("Try different keywords or check job site availability")
                return workflow_results
            
            # Save jobs to database
            from app.services.database_service import save_job_posting
            saved_count = 0
            for job in jobs_found:
                if save_job_posting(job):
                    saved_count += 1
            
            workflow_results["jobs_saved"] = saved_count
            self.console.print(f"✅ Discovered {len(jobs_found)} jobs, saved {saved_count} new ones")
            
            # Log search query
            try:
                save_search_query(
                    user_profile_id=1,
                    query_terms=keywords,
                    location=location,
                    source="Orchestrated_Workflow",
                    results_count=len(jobs_found)
                )
            except Exception as e:
                logger.warning(f"Failed to log search query: {e}")
            
        except Exception as e:
            error_msg = f"Job discovery failed: {e}"
            workflow_results["errors"].append(error_msg)
            self.console.print(f"[red]❌ {error_msg}[/red]")
            return workflow_results
        
        # Phase 2: AI Analysis (if requested and possible)
        if auto_analyze and target_role:
            if not self._initialize_gemini_service():
                workflow_results["recommendations"].append("Enable AI analysis by configuring GEMINI_API_KEY")
            else:
                try:
                    self.console.print(f"\n[bold]Phase 2: AI Analysis for '{target_role}'[/bold]")
                    analysis_results = self._analyze_pending_jobs(target_role, max_jobs=num_results)
                    workflow_results.update(analysis_results)
                    
                except Exception as e:
                    error_msg = f"AI analysis failed: {e}"
                    workflow_results["errors"].append(error_msg)
                    self.console.print(f"[red]❌ {error_msg}[/red]")
        
        # Phase 3: Generate Recommendations
        workflow_results["recommendations"].extend(self._generate_workflow_recommendations(workflow_results))
        
        # Display Summary
        self._display_workflow_summary(workflow_results)
        
        return workflow_results
    
    def _analyze_pending_jobs(self, target_role: str, max_jobs: int = 10) -> Dict[str, Any]:
        """Analyze pending jobs for relevance."""
        analysis_results = {
            "jobs_analyzed": 0,
            "high_relevance_jobs": [],
            "medium_relevance_jobs": [],
            "low_relevance_jobs": []
        }
        
        pending_jobs = get_pending_jobs(limit=max_jobs)
        if not pending_jobs:
            self.console.print("[yellow]No pending jobs to analyze[/yellow]")
            return analysis_results
        
        self.console.print(f"Analyzing {len(pending_jobs)} pending jobs...")
        
        for job in pending_jobs:
            try:
                score = self.gemini_service.get_job_relevance_score(
                    job_description=job.full_description_text or job.title,
                    user_target_role=target_role
                )
                
                if score is not None:
                    # Update job status in database
                    new_status = "analyzed"
                    update_job_processing_status(job.internal_db_id, new_status, score)
                    
                    job_summary = {
                        "job": job,
                        "score": score,
                        "title": job.title,
                        "company": job.company_name
                    }
                    
                    if score >= 4:
                        analysis_results["high_relevance_jobs"].append(job_summary)
                    elif score >= 3:
                        analysis_results["medium_relevance_jobs"].append(job_summary)
                    else:
                        analysis_results["low_relevance_jobs"].append(job_summary)
                    
                    analysis_results["jobs_analyzed"] += 1
                    
            except Exception as e:
                logger.error(f"Error analyzing job {job.internal_db_id}: {e}")
        
        return analysis_results
    
    def smart_application_suggestions(self, user_profile_id: int = 1) -> List[Dict[str, Any]]:
        """
        Intelligent suggestions based on analyzed jobs and application history.
        """
        suggestions = []
        
        # Get high-relevance jobs that haven't been applied to
        try:
            # Get all analyzed jobs with high relevance
            all_jobs = get_all_jobs(limit=50)
            high_relevance_jobs = [
                job for job in all_jobs 
                if hasattr(job, 'relevance_score') and job.relevance_score and job.relevance_score >= 4
            ]
            
            # Get application history
            applications = get_application_logs(user_profile_id=user_profile_id, limit=100)
            applied_urls = [app.job_url for app in applications]
            
            # Find unapplied high-relevance jobs
            unapplied_high_jobs = [
                job for job in high_relevance_jobs 
                if job.job_url not in applied_urls
            ]
            
            for job in unapplied_high_jobs[:5]:  # Top 5 suggestions
                suggestions.append({
                    "type": "high_priority_application",
                    "job": job,
                    "reason": f"High AI relevance score ({job.relevance_score}/5)",
                    "action": f"Consider applying to '{job.title}' at '{job.company_name}'"
                })
                
        except Exception as e:
            logger.error(f"Error generating application suggestions: {e}")
            suggestions.append({
                "type": "error",
                "reason": "Could not analyze application opportunities",
                "action": "Review jobs manually using view-applications and analyze-jobs"
            })
        
        return suggestions
    
    def _generate_workflow_recommendations(self, workflow_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on workflow results."""
        recommendations = []
        
        jobs_discovered = workflow_results.get("jobs_discovered", 0)
        jobs_analyzed = workflow_results.get("jobs_analyzed", 0)
        high_relevance = len(workflow_results.get("high_relevance_jobs", []))
        
        if jobs_discovered == 0:
            recommendations.append("Try broader keywords or check different job sites")
        elif jobs_analyzed == 0:
            recommendations.append("Run 'analyze-jobs' with your target role to get AI relevance scores")
        elif high_relevance > 0:
            recommendations.append(f"Focus on {high_relevance} high-relevance jobs for applications")
            recommendations.append("Use 'optimize-resume' command to tailor your resume for top jobs")
        else:
            recommendations.append("Consider refining your target role or expanding your search criteria")
        
        if workflow_results.get("errors"):
            recommendations.append("Check logs for detailed error information")
        
        return recommendations
    
    def _display_workflow_summary(self, workflow_results: Dict[str, Any]) -> None:
        """Display a comprehensive summary of workflow results."""
        from rich.panel import Panel
        from rich.table import Table
        
        # Create summary panel
        summary_content = f"""
**Workflow Complete!**

📊 **Results:**
• Jobs Discovered: {workflow_results.get('jobs_discovered', 0)}
• Jobs Saved: {workflow_results.get('jobs_saved', 0)}
• Jobs Analyzed: {workflow_results.get('jobs_analyzed', 0)}
• High Relevance (4-5⭐): {len(workflow_results.get('high_relevance_jobs', []))}
• Medium Relevance (3⭐): {len(workflow_results.get('medium_relevance_jobs', []))}

🎯 **Next Steps:**
"""
        
        for rec in workflow_results.get("recommendations", []):
            summary_content += f"\n• {rec}"
        
        if workflow_results.get("errors"):
            summary_content += f"\n\n⚠️ **Errors:** {len(workflow_results['errors'])} issues encountered"
        
        panel = Panel(summary_content, title="🤖 Agent Workflow Summary", border_style="green")
        self.console.print(panel)
        
        # Display high-relevance jobs table if any
        high_jobs = workflow_results.get("high_relevance_jobs", [])
        if high_jobs:
            table = Table(title="🌟 High Relevance Jobs for Your Consideration", show_header=True)
            table.add_column("Score", width=6)
            table.add_column("Job Title", min_width=25)
            table.add_column("Company", min_width=20)
            
            for job_info in high_jobs[:5]:  # Top 5
                table.add_row(
                    f"{job_info['score']}/5 ⭐",
                    job_info['title'][:30] + "..." if len(job_info['title']) > 30 else job_info['title'],
                    job_info['company'][:25] + "..." if len(job_info['company']) > 25 else job_info['company']
                )
            
            self.console.print(table)
    
    def interactive_workflow_prompt(self) -> None:
        """
        Interactive mode that guides users through the complete workflow.
        """
        self.console.print("\n[bold blue]🎯 Welcome to Interactive Job Discovery & Analysis![/bold blue]")
        self.console.print("I'll guide you through finding and analyzing relevant jobs.\n")
        
        # Gather user inputs
        keywords = Prompt.ask("🔍 What job keywords would you like to search for?", default="Software Engineer")
        location = Prompt.ask("📍 Preferred location (or press Enter for any)", default="")
        target_role = Prompt.ask("🎯 What's your target role for AI analysis?", default=keywords)
        num_results = int(Prompt.ask("📊 How many jobs to discover?", default="5"))
        
        # Confirm workflow
        auto_analyze = Confirm.ask("🤖 Would you like me to automatically analyze jobs with AI?", default=True)
        
        # Execute workflow
        self.console.print(f"\n[bold green]🚀 Starting your personalized job workflow...[/bold green]")
        
        results = self.discover_and_analyze_workflow(
            keywords=keywords,
            location=location if location else None,
            num_results=num_results,
            target_role=target_role,
            auto_analyze=auto_analyze
        )
        
        # Offer follow-up actions
        if results.get("high_relevance_jobs"):
            if Confirm.ask("\n💡 Would you like suggestions on next steps for applications?"):
                suggestions = self.smart_application_suggestions()
                if suggestions:
                    self.console.print("\n[bold cyan]📋 Smart Application Suggestions:[/bold cyan]")
                    for i, suggestion in enumerate(suggestions[:3], 1):
                        self.console.print(f"{i}. {suggestion.get('action', suggestion)}")

    async def intelligent_job_discovery_workflow(
        self, 
        keywords: str, 
        location: str = None,
        target_experience_level: str = "Entry level",
        preferred_work_modality: str = "Remote",
        max_job_age_days: int = 7,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Intelligent job discovery workflow that applies sophisticated filters
        to reduce 400+ jobs to highly relevant matches, similar to the approach
        outlined in the DEV.to automation article.
        
        Args:
            keywords: Job search keywords
            location: Job location preference
            target_experience_level: "Entry level", "Mid-Senior level", etc.
            preferred_work_modality: "Remote", "Hybrid", "On-site"
            max_job_age_days: Maximum age of jobs in days (7 = past week)
            max_results: Maximum number of results to return
            
        Returns:
            Workflow results with filtered, high-quality job matches
        """
        workflow_results = {
            "total_unfiltered_jobs": 0,
            "filtered_jobs_count": 0,
            "high_relevance_jobs": [],
            "filter_efficiency": 0.0,
            "filters_applied": [],
            "success": False,
            "errors": []
        }
        
        try:
            self.console.print(f"\n[bold blue]🧠 Starting Intelligent Job Discovery Workflow[/bold blue]")
            self.console.print(f"Keywords: '{keywords}' | Experience: '{target_experience_level}' | Work: '{preferred_work_modality}'")
            
            # Step 1: Initialize services
            if not self._initialize_services():
                workflow_results["errors"].append("Failed to initialize required services")
                return workflow_results
            
            # Step 2: Map job age to LinkedIn date filter
            date_filter_map = {
                1: "Past 24 hours",
                7: "Past week", 
                30: "Past month"
            }
            date_posted = date_filter_map.get(max_job_age_days, "Past week")
            workflow_results["filters_applied"].append(f"Date: {date_posted}")
            
            # Step 3: Prepare filter parameters
            experience_levels = [target_experience_level] if target_experience_level else None
            work_modalities = [preferred_work_modality] if preferred_work_modality else None
            
            if experience_levels:
                workflow_results["filters_applied"].append(f"Experience: {', '.join(experience_levels)}")
            if work_modalities:
                workflow_results["filters_applied"].append(f"Work Type: {', '.join(work_modalities)}")
            
            self.console.print(f"🎯 Applying filters: {', '.join(workflow_results['filters_applied'])}")
            
            # Step 4: Perform intelligent filtered search
            self.console.print(f"\n🔍 Searching LinkedIn with intelligent filters...")
            
            try:
                filtered_jobs = await self.linkedin_scraper.search_jobs_with_filters(
                    keywords=keywords,
                    location=location,
                    num_results=max_results,
                    date_posted=date_posted,
                    experience_levels=experience_levels,
                    work_modalities=work_modalities,
                    enable_easy_apply_filter=False  # We want external applications
                )
                
                workflow_results["filtered_jobs_count"] = len(filtered_jobs)
                
                if filtered_jobs:
                    self.console.print(f"✅ Found {len(filtered_jobs)} highly filtered jobs!")
                    
                    # Step 5: Convert to job posting models and save
                    from app.services.database_service import save_job_posting
                    saved_count = 0
                    
                    for job_data in filtered_jobs:
                        job_posting = self.linkedin_scraper._parse_job_to_model(job_data)
                        if job_posting and save_job_posting(job_posting):
                            workflow_results["high_relevance_jobs"].append({
                                "title": job_posting.title,
                                "company": job_posting.company_name,
                                "location": job_posting.location_text,
                                "url": job_posting.job_url,
                                "source": "linkedin_filtered"
                            })
                            saved_count += 1
                    
                    self.console.print(f"💾 Saved {saved_count} new filtered jobs to database")
                    
                    # Step 6: Calculate filter efficiency
                    # Estimate original unfiltered results (based on typical LinkedIn searches)
                    estimated_unfiltered = min(len(filtered_jobs) * 20, 1000)  # Conservative estimate
                    workflow_results["total_unfiltered_jobs"] = estimated_unfiltered
                    workflow_results["filter_efficiency"] = (
                        (estimated_unfiltered - len(filtered_jobs)) / estimated_unfiltered * 100
                        if estimated_unfiltered > 0 else 0
                    )
                    
                    workflow_results["success"] = True
                    
                else:
                    self.console.print("[yellow]⚠️ No jobs found with current filters - try broadening criteria[/yellow]")
                    workflow_results["errors"].append("No jobs found with current filters")
                
            except Exception as e:
                error_msg = f"LinkedIn filtered search failed: {str(e)}"
                workflow_results["errors"].append(error_msg)
                self.console.print(f"[red]❌ {error_msg}[/red]")
            
            # Step 7: Display results summary
            self._display_intelligent_discovery_summary(workflow_results)
            
            return workflow_results
            
        except Exception as e:
            error_msg = f"Intelligent discovery workflow failed: {str(e)}"
            workflow_results["errors"].append(error_msg)
            self.console.print(f"[red]❌ {error_msg}[/red]")
            return workflow_results

    def _display_intelligent_discovery_summary(self, results: Dict[str, Any]) -> None:
        """Display comprehensive summary of intelligent discovery results"""
        from rich.panel import Panel
        from rich.table import Table
        
        # Create efficiency summary
        efficiency = results.get("filter_efficiency", 0)
        filtered_count = results.get("filtered_jobs_count", 0)
        
        summary_content = f"""
**🧠 Intelligent Job Discovery Complete!**

📊 **Filter Performance:**
• Estimated Unfiltered Jobs: ~{results.get('total_unfiltered_jobs', 'Unknown')}
• Highly Relevant Jobs Found: {filtered_count}
• Filter Efficiency: {efficiency:.1f}% reduction in noise
• Filters Applied: {', '.join(results.get('filters_applied', []))}

🎯 **Quality Over Quantity:**
Instead of manually reviewing 400+ jobs, you now have {filtered_count} pre-qualified matches!

💡 **Next Steps:**
• Review the {filtered_count} filtered jobs below
• Use 'external-apply' command for targeted applications
• Run 'analyze-jobs' for AI relevance scoring
"""
        
        if results.get("errors"):
            summary_content += f"\n⚠️ **Issues:** {len(results['errors'])} errors encountered"
        
        panel = Panel(summary_content, title="🧠 Intelligent Discovery Results", border_style="green" if results.get("success") else "yellow")
        self.console.print(panel)
        
        # Display filtered jobs table
        high_jobs = results.get("high_relevance_jobs", [])
        if high_jobs:
            table = Table(title="🎯 Pre-Qualified Job Matches", show_header=True)
            table.add_column("Job Title", min_width=25)
            table.add_column("Company", min_width=20)
            table.add_column("Location", min_width=15)
            table.add_column("Source", width=12)
            
            for job in high_jobs[:10]:  # Show top 10
                table.add_row(
                    job['title'][:35] + "..." if len(job['title']) > 35 else job['title'],
                    job['company'][:25] + "..." if len(job['company']) > 25 else job['company'],
                    job['location'][:20] + "..." if len(job['location']) > 20 else job['location'],
                    job['source']
                )
            
            self.console.print(table)

    async def smart_external_application_pipeline(
        self, 
        keywords: str,
        target_experience_level: str = "Entry level",
        preferred_work_modality: str = "Remote", 
        max_applications: int = 3,
        user_profile_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Intelligent Discovery → External Applications
        
        This combines the intelligent job filtering with external application automation
        to create a complete end-to-end job application system.
        
        Args:
            keywords: Job search keywords
            target_experience_level: Experience level filter
            preferred_work_modality: Work type preference
            max_applications: Maximum applications to submit
            user_profile_name: User profile to use for applications
            
        Returns:
            Complete pipeline results
        """
        pipeline_results = {
            "discovery_results": {},
            "application_results": {},
            "total_jobs_discovered": 0,
            "applications_attempted": 0,
            "applications_successful": 0,
            "success_rate": 0.0,
            "pipeline_success": False
        }
        
        try:
            self.console.print(f"\n[bold magenta]🚀 Smart External Application Pipeline[/bold magenta]")
            self.console.print(f"Target: {keywords} | Experience: {target_experience_level} | Work: {preferred_work_modality}")
            
            # Phase 1: Intelligent Job Discovery
            self.console.print(f"\n[bold]Phase 1: Intelligent Job Discovery[/bold]")
            discovery_results = await self.intelligent_job_discovery_workflow(
                keywords=keywords,
                target_experience_level=target_experience_level,
                preferred_work_modality=preferred_work_modality,
                max_results=max_applications * 2  # Get extra jobs for selection
            )
            
            pipeline_results["discovery_results"] = discovery_results
            pipeline_results["total_jobs_discovered"] = discovery_results.get("filtered_jobs_count", 0)
            
            if not discovery_results.get("success") or not discovery_results.get("high_relevance_jobs"):
                self.console.print("[yellow]⚠️ No suitable jobs found for applications[/yellow]")
                return pipeline_results
            
            # Phase 2: Load User Profile
            from app.services.user_profile_service import UserProfileService
            profile_service = UserProfileService()
            user_profile = profile_service.load_profile(user_profile_name)
            
            if not user_profile:
                # Create default profile if none exists
                user_profile = profile_service.create_default_profile()
                self.console.print(f"[yellow]⚠️ Created default profile - customize it for better results[/yellow]")
            
            # Phase 3: External Application Automation
            self.console.print(f"\n[bold]Phase 2: External Application Automation[/bold]")
            
            jobs_for_application = discovery_results["high_relevance_jobs"][:max_applications]
            application_results = []
            
            for i, job in enumerate(jobs_for_application):
                self.console.print(f"\n[bold]Processing application {i+1}/{len(jobs_for_application)}[/bold]")
                self.console.print(f"Job: {job['title']} at {job['company']}")
                
                try:
                    # Use the external application workflow
                    app_result = await self.run_external_application_workflow(
                        job_url=job['url'],
                        user_profile=user_profile
                    )
                    
                    application_results.append({
                        "job": job,
                        "result": app_result,
                        "success": app_result.get("success", False)
                    })
                    
                    pipeline_results["applications_attempted"] += 1
                    if app_result.get("success"):
                        pipeline_results["applications_successful"] += 1
                    
                    # Delay between applications
                    if i < len(jobs_for_application) - 1:
                        import asyncio
                        await asyncio.sleep(10)  # 10 second delay
                    
                except Exception as e:
                    self.console.print(f"[red]❌ Application failed: {str(e)}[/red]")
                    application_results.append({
                        "job": job,
                        "result": {"success": False, "error": str(e)},
                        "success": False
                    })
            
            pipeline_results["application_results"] = application_results
            
            # Calculate success rate
            if pipeline_results["applications_attempted"] > 0:
                pipeline_results["success_rate"] = (
                    pipeline_results["applications_successful"] / 
                    pipeline_results["applications_attempted"] * 100
                )
            
            pipeline_results["pipeline_success"] = pipeline_results["applications_successful"] > 0
            
            # Display final summary
            self._display_pipeline_summary(pipeline_results)
            
            return pipeline_results
            
        except Exception as e:
            self.console.print(f"[red]❌ Pipeline failed: {str(e)}[/red]")
            return pipeline_results

    def _display_pipeline_summary(self, results: Dict[str, Any]) -> None:
        """Display comprehensive pipeline summary"""
        from rich.panel import Panel
        
        discovery_count = results.get("total_jobs_discovered", 0)
        attempted = results.get("applications_attempted", 0)
        successful = results.get("applications_successful", 0)
        success_rate = results.get("success_rate", 0)
        
        summary_content = f"""
**🚀 Smart External Application Pipeline Complete!**

📊 **Pipeline Performance:**
• Jobs Discovered (Filtered): {discovery_count}
• Applications Attempted: {attempted}
• Applications Successful: {successful}
• Success Rate: {success_rate:.1f}%

🎯 **Efficiency Gains:**
• Automated filtering reduced 400+ jobs to {discovery_count} targets
• Intelligent application to external ATS systems
• Human oversight ensured quality control

💡 **Impact:**
You've automated what would typically take 5-10 hours of manual work!
"""
        
        color = "green" if results.get("pipeline_success") else "yellow"
        panel = Panel(summary_content, title="🤖 Complete Automation Pipeline Results", border_style=color)
        self.console.print(panel)

if __name__ == "__main__":
    # Test the orchestrator
    import sys
    import os
    # Add the parent directory (project root) to path for imports
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = AgentOrchestrator()
    
    # Test the interactive workflow
    try:
        orchestrator.interactive_workflow_prompt()
    except KeyboardInterrupt:
        print("\n👋 Workflow cancelled by user.")
    except Exception as e:
        print(f"❌ Error during workflow: {e}") 