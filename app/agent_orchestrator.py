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

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Central orchestrator for coordinating AI job application workflows.
    Manages intelligent automation between job discovery, analysis, and application tracking.
    """
    
    def __init__(self):
        self.console = Console()
        self.gemini_service = None
        
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