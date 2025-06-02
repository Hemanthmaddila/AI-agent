# Main CLI Entry Point - Command line interface for the AI agent 
import typer
from rich.console import Console
from rich.table import Table # Import Table for displaying results
import os # For path operations
import sys # For stdout logging handler
import logging # Import logging
from typing import List # For type hinting
from typing_extensions import Annotated # For newer Typer versions
from datetime import datetime
import asyncio # For Phase 5.1 async operations

# Add UTF-8 encoding support for Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

# Assuming your settings and future orchestrator/services will be in the 'app' package
# and config.settings loads everything we need.
from config import settings # This will load .env and make settings available
# Import the Playwright scraper service (replaces SerpAPI for MVP)
from app.services.playwright_scraper_service import search_jobs_sync
# Import the DatabaseService functions including new application logging
from app.services.database_service import (
    save_job_posting, save_search_query, get_pending_jobs, update_job_processing_status, 
    save_application_log, find_job_by_url, get_application_logs, get_all_jobs,
    # New Phase 5.1 functions
    add_embedding_columns_if_not_exist, save_job_embeddings, update_semantic_scores,
    get_jobs_needing_embeddings, get_jobs_with_embeddings
)
# Import the GeminiService
from app.services.gemini_service import GeminiService
# Phase 5.1: Import Semantic Analysis Service
from app.services.semantic_analysis_service import get_semantic_analysis_service
# Phase 4.2: Import Application Automation Services
from app.application_automation.form_filler import get_form_filler_service, FormFillerService
from app.hitl.hitl_service import get_hitl_service
# We will also need our JobPosting model for type hinting and potentially for displaying
from app.models.job_posting_models import JobPosting
from app.models.application_log_models import ApplicationLog
from app.models.user_profile_models import UserProfile
# Import the AgentOrchestrator
from app.agent_orchestrator import AgentOrchestrator

# Initialize Rich Console for better output
console = Console()
app = typer.Typer(help="🤖 AI Job Application Agent - Your Personal Career Assistant!")

# --- Logging Setup (Basic) ---
# Ensure log directory exists (moved this setup to be more global for the app)
if not os.path.exists(settings.LOG_DIR):
    os.makedirs(settings.LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE_PATH),
        logging.StreamHandler(sys.stdout) # Ensure logs also go to console
    ]
)
logger = logging.getLogger(__name__)

# --- Utility function for initial setup (like checking API keys) ---
def check_initial_setup():
    """Checks for essential configurations like API keys."""
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not configured in .env file.")
        console.print("[bold yellow]WARNING: GEMINI_API_KEY is not configured. AI features will be limited.[/bold yellow]")
    # No need for a separate console print if logger is also printing to console.
    # We'll do a specific check for SERPAPI_API_KEY in the find_jobs command itself for now.

@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """
    AI Job Application Agent CLI.
    Called before any command. Use `invoke_without_command=True` to allow it to run if no subcommand is passed.
    """
    logger.info("AI Job Application Agent CLI Initialized.")
    check_initial_setup()
    if ctx.invoked_subcommand is None:
        console.print("Welcome! Use '--help' to see available commands.")

@app.command()
def find_jobs(
    keywords: Annotated[str, typer.Option(help="Keywords for the job search (e.g., 'Python Developer').")],
    location: Annotated[str, typer.Option(help="Location for the job search (optional, mainly for remote jobs).")] = None,
    num_results: Annotated[int, typer.Option(help="Number of results to fetch.")] = 10
):
    """
    Finds job postings by web scraping Remote.co based on keywords.
    Saves results to the database for further processing.
    """
    console.print(f"\n[bold blue]🔎 Scraping jobs from Remote.co with keywords '{keywords}'[/bold blue]")
    if location:
        console.print(f"Location preference: '{location}' (note: Remote.co focuses on remote positions)")
    console.print(f"Number of results to fetch: {num_results}")
    logger.info(f"find_jobs command initiated with keywords: '{keywords}', location: '{location}', num_results: {num_results}")

    # Note: No API key required for web scraping!
    console.print("[dim]Using Playwright web scraper - no API keys required![/dim]")
        
    try:
        console.print("🌐 Launching browser and navigating to Remote.co...")
        
        # Use the Playwright scraper instead of SerpAPI
        jobs_found: List[JobPosting] = search_jobs_sync(
            keywords=keywords, 
            location=location, 
            num_results=num_results
        )

        if jobs_found:
            console.print(f"\n[bold green]✅ Scraped {len(jobs_found)} jobs. Saving to database...[/bold green]")
            
            # Save jobs to database and track saved count
            saved_count = 0
            skipped_count = 0
            
            for job in jobs_found:
                job_id = save_job_posting(job)
                if job_id:
                    saved_count += 1
                    logger.debug(f"Saved job '{job.title}' with DB ID: {job_id}")
                else:
                    skipped_count += 1
                    logger.warning(f"Failed to save or duplicate job: '{job.title}' from '{job.company_name}'")
            
            # Log the search query for tracking
            try:
                search_id = save_search_query(
                    user_profile_id=1,  # Using default user profile for MVP
                    query_terms=keywords,
                    location=location,
                    source="Remote.co_Playwright",
                    results_count=len(jobs_found)
                )
                logger.info(f"Logged search query with ID: {search_id}")
            except Exception as e:
                logger.warning(f"Failed to log search query: {e}")
            
            # Display results table
            table = Table(title=f"Jobs Scraped from Remote.co (Saved: {saved_count}, Skipped: {skipped_count})")
            table.add_column("No.", style="dim", width=4)
            table.add_column("Title", style="cyan", min_width=30)
            table.add_column("Company", style="magenta", min_width=20)
            table.add_column("Location", style="yellow", min_width=15)
            table.add_column("Status", style="green", min_width=10)

            for i, job in enumerate(jobs_found):
                # Check if this job was saved or skipped
                status = "💾 Saved" if i < saved_count else "⏭️ Skipped"
                table.add_row(
                    str(i + 1),
                    job.title if job.title else "N/A",
                    job.company_name if job.company_name else "N/A",
                    job.location_text if job.location_text else "N/A",
                    status
                )
            console.print(table)
            
            logger.info(f"Job scraping completed. Saved: {saved_count}, Skipped: {skipped_count}")
            
            # Summary message
            if saved_count > 0:
                console.print(f"\n[bold green]✅ Successfully saved {saved_count} jobs to the database![/bold green]")
                console.print("💡 Next steps:")
                console.print("  • Run AI analysis on saved jobs to calculate relevance scores")
                console.print("  • Review and select jobs for application")
                console.print("  • Use 'log-application' command to track applications")
                console.print(f"\n[dim]Source: Remote.co (web scraping with Playwright)[/dim]")
            else:
                console.print(f"\n[bold yellow]⚠️ No new jobs were saved (all {skipped_count} were duplicates or errors).[/bold yellow]")
                
        else:
            console.print("[yellow]No jobs found for the given criteria on Remote.co.[/yellow]")
            console.print("💡 Try different keywords or check Remote.co manually to verify job availability.")
            logger.info("No jobs found from Remote.co scraping for the given criteria.")
            
            # Still log the search query even if no results
            try:
                search_id = save_search_query(
                    user_profile_id=1,
                    query_terms=keywords,
                    location=location,
                    source="Remote.co_Playwright",
                    results_count=0
                )
                logger.info(f"Logged empty search query with ID: {search_id}")
            except Exception as e:
                logger.warning(f"Failed to log empty search query: {e}")

    except Exception as e:
        logger.error(f"An unexpected error occurred during job scraping: {e}", exc_info=True)
        console.print(f"[bold red]Scraping Error: {e}[/bold red]")
        console.print("💡 This might be due to:")
        console.print("  • Network connectivity issues")
        console.print("  • Changes in Remote.co website structure")
        console.print("  • Browser/Playwright installation issues")
        raise typer.Exit(code=1)

@app.command()
def analyze_jobs(
    target_role: Annotated[str, typer.Option(help="Your target role for relevance analysis (e.g., 'Python Developer').")] = "Software Developer",
    max_jobs: Annotated[int, typer.Option(help="Maximum number of jobs to analyze.")] = 10
):
    """
    Analyzes saved job postings using AI to calculate relevance scores.
    Updates the database with AI-generated relevance scores (1-5 scale).
    """
    console.print(f"\n[bold blue]🤖 Starting AI analysis of saved jobs for role: '{target_role}'[/bold blue]")
    console.print(f"Maximum jobs to analyze: {max_jobs}")
    logger.info(f"analyze_jobs command initiated with target_role: '{target_role}', max_jobs: {max_jobs}")

    # Check if Gemini API key is configured
    if not settings.GEMINI_API_KEY:
        console.print("[bold red]❌ GEMINI_API_KEY is not configured![/bold red]")
        console.print("Please add your Gemini API key to the .env file:")
        console.print("1. Get a free API key from: https://makersuite.google.com/app/apikey")
        console.print("2. Create a .env file with: GEMINI_API_KEY=your_api_key_here")
        logger.error("analyze_jobs command failed: GEMINI_API_KEY not configured")
        raise typer.Exit(code=1)
        
    try:
        # Initialize Gemini service
        console.print("🧠 Initializing AI service...")
        gemini_service = GeminiService()
        
        # Get pending jobs from database
        console.print("📋 Retrieving saved jobs from database...")
        pending_jobs = get_pending_jobs(limit=max_jobs)
        
        if not pending_jobs:
            console.print("[yellow]No pending jobs found in the database.[/yellow]")
            console.print("💡 Run 'find-jobs' first to discover and save some job postings.")
            logger.info("No pending jobs found for analysis")
            return
        
        console.print(f"Found {len(pending_jobs)} jobs to analyze")
        
        # Analyze each job
        analyzed_count = 0
        skipped_count = 0
        results = []
        
        with console.status("[bold green]Analyzing jobs with AI...") as status:
            for i, job in enumerate(pending_jobs, 1):
                status.update(f"[bold green]Analyzing job {i}/{len(pending_jobs)}: {job.title[:30]}...")
                logger.info(f"Analyzing job {i}/{len(pending_jobs)}: '{job.title}' from '{job.company_name}'")
                
                try:
                    # Get AI relevance score
                    relevance_score = gemini_service.get_job_relevance_score(
                        job_description=job.full_description_text or job.title,
                        user_target_role=target_role
                    )
                    
                    if relevance_score is not None:
                        # Update the job in the database
                        update_success = update_job_processing_status(
                            job_db_id=job.internal_db_id,
                            new_status="analyzed",
                            relevance_score=relevance_score
                        )
                        
                        if update_success:
                            analyzed_count += 1
                            results.append({
                                'job': job,
                                'score': relevance_score,
                                'status': 'analyzed'
                            })
                            logger.info(f"Successfully analyzed and updated job {job.internal_db_id} with score {relevance_score}")
                        else:
                            skipped_count += 1
                            results.append({
                                'job': job,
                                'score': relevance_score,
                                'status': 'update_failed'
                            })
                            logger.warning(f"Got score {relevance_score} but failed to update job {job.internal_db_id}")
                    else:
                        skipped_count += 1
                        results.append({
                            'job': job,
                            'score': None,
                            'status': 'ai_failed'
                        })
                        logger.warning(f"Failed to get AI score for job {job.internal_db_id}")
                        
                except Exception as e:
                    skipped_count += 1
                    results.append({
                        'job': job,
                        'score': None,
                        'status': 'error'
                    })
                    logger.error(f"Error analyzing job {job.internal_db_id}: {e}")
        
        # Display results
        console.print(f"\n[bold green]✅ AI Analysis Complete![/bold green]")
        console.print(f"Analyzed: {analyzed_count}, Skipped: {skipped_count}")
        
        # Create results table
        table = Table(title=f"AI Job Relevance Analysis Results (Target Role: {target_role})")
        table.add_column("No.", style="dim", width=4)
        table.add_column("Title", style="cyan", min_width=25)
        table.add_column("Company", style="magenta", min_width=20)
        table.add_column("AI Score", style="bold", width=8)
        table.add_column("Status", style="green", width=12)

        for i, result in enumerate(results, 1):
            job = result['job']
            score = result['score']
            status = result['status']
            
            # Format score with emoji
            if score is not None:
                if score >= 4:
                    score_display = f"⭐ {score}/5"
                elif score >= 3:
                    score_display = f"👍 {score}/5"
                else:
                    score_display = f"📝 {score}/5"
            else:
                score_display = "❌ N/A"
            
            # Format status
            status_display = {
                'analyzed': '✅ Analyzed',
                'update_failed': '⚠️ Score Only',
                'ai_failed': '❌ AI Failed',
                'error': '💥 Error'
            }.get(status, '❓ Unknown')
            
            table.add_row(
                str(i),
                job.title[:25] + "..." if len(job.title) > 25 else job.title,
                job.company_name[:20] + "..." if len(job.company_name) > 20 else job.company_name,
                score_display,
                status_display
            )
        
        console.print(table)
        
        # Summary and next steps
        if analyzed_count > 0:
            high_relevance = sum(1 for r in results if r['score'] and r['score'] >= 4)
            medium_relevance = sum(1 for r in results if r['score'] and 3 <= r['score'] < 4)
            
            console.print(f"\n[bold blue]📊 Analysis Summary:[/bold blue]")
            console.print(f"⭐ High relevance (4-5): {high_relevance} jobs")
            console.print(f"👍 Medium relevance (3): {medium_relevance} jobs")
            console.print(f"📝 Lower relevance (1-2): {analyzed_count - high_relevance - medium_relevance} jobs")
            
            console.print(f"\n💡 Next steps:")
            console.print("  • Review high-relevance jobs for application")
            console.print("  • Use 'log-application' command when you apply")
            console.print("  • Run 'find-jobs' again to discover more opportunities")
        
        logger.info(f"Job analysis completed. Analyzed: {analyzed_count}, Skipped: {skipped_count}")
        
    except ValueError as ve:
        # This catches GeminiService initialization errors
        console.print(f"[bold red]Configuration Error: {ve}[/bold red]")
        console.print("Please check your GEMINI_API_KEY configuration.")
        logger.error(f"GeminiService initialization failed: {ve}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during job analysis: {e}", exc_info=True)
        console.print(f"[bold red]Analysis Error: {e}[/bold red]")
        console.print("💡 This might be due to:")
        console.print("  • Network connectivity issues")
        console.print("  • Gemini API service problems")
        console.print("  • Database access issues")
        raise typer.Exit(code=1)

@app.command()
def log_application(
    job_url: Annotated[str, typer.Option(help="The URL of the job you applied for.")],
    resume_path: Annotated[str, typer.Option(help="Path to the resume version used for this application.")], 
    status: Annotated[str, typer.Option(help="Status of the application (e.g., 'Applied', 'Submitted').")] = "Applied",
    notes: Annotated[str, typer.Option(help="Any notes about this application.")] = None,
    job_title: Annotated[str, typer.Option(help="Job title (will auto-detect from database if available).")] = None,
    company_name: Annotated[str, typer.Option(help="Company name (will auto-detect from database if available).")] = None
):
    """
    Logs a job application to the database with automatic job detection.
    """
    console.print(f"\n[bold blue]📝 Logging application for job URL: [cyan]{job_url}[/cyan][/bold blue]")
    logger.info(f"log_application command initiated for job_url: {job_url}")

    try:
        # Try to find the job in our database first
        console.print("🔍 Searching for job details in database...")
        found_job = find_job_by_url(job_url)
        
        # Determine job details
        final_job_title = job_title or (found_job.title if found_job else None)
        final_company_name = company_name or (found_job.company_name if found_job else None)
        job_posting_id = found_job.internal_db_id if found_job else None
        
        # If job details are still missing, prompt user or use defaults
        if not final_job_title:
            final_job_title = typer.prompt("Job title not found in database. Please enter job title")
        
        if not final_company_name:
            final_company_name = typer.prompt("Company name not found in database. Please enter company name")
        
        # Validate resume path exists
        if not os.path.exists(resume_path):
            console.print(f"[yellow]⚠️  Warning: Resume file '{resume_path}' not found. Continuing anyway...[/yellow]")
            logger.warning(f"Resume file not found: {resume_path}")
        
        # Create ApplicationLog object
        application_log = ApplicationLog(
            job_url=job_url,
            job_title=final_job_title,
            company_name=final_company_name,
            application_date=datetime.utcnow(),
            status=status.lower(),
            resume_version_used_path=resume_path,  # Full path as expected by model
            notes=notes
        )
        
        # Save to database
        console.print("💾 Saving application log to database...")
        application_id = save_application_log(application_log)
        
        if application_id:
            console.print(f"\n[bold green]✅ Application logged successfully![/bold green]")
            
            # Display summary table
            table = Table(title="Application Log Summary")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Database ID", str(application_id))
            table.add_row("Job Title", final_job_title)
            table.add_row("Company", final_company_name)
            table.add_row("Status", status)
            table.add_row("Resume Used", os.path.basename(resume_path))
            table.add_row("Job URL", job_url[:50] + "..." if len(job_url) > 50 else job_url)
            table.add_row("In Our Database", "✅ Yes" if found_job else "❌ No")
            if notes:
                table.add_row("Notes", notes)
            
            console.print(table)
            
            # Show next steps
            console.print(f"\n💡 Next steps:")
            console.print("  • Track application status updates")
            console.print("  • Use 'view-applications' to see all logged applications")
            if not found_job:
                console.print("  • Consider adding this job to database with 'find-jobs' for AI analysis")
            
            logger.info(f"Successfully logged application with ID {application_id} for '{final_job_title}' at '{final_company_name}'")
            
        else:
            console.print("[bold red]❌ Failed to save application log to database.[/bold red]")
            logger.error("Failed to save application log to database")
            raise typer.Exit(code=1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        raise typer.Exit(code=0)
    except Exception as e:
        logger.error(f"An unexpected error occurred during log_application: {e}", exc_info=True)
        console.print(f"[bold red]Error logging application: {e}[/bold red]")
        console.print("💡 This might be due to:")
        console.print("  • Database connection issues")
        console.print("  • Invalid input parameters")
        console.print("  • Disk space or permission issues")
        raise typer.Exit(code=1)

@app.command()
def view_applications(
    limit: Annotated[int, typer.Option(help="Maximum number of applications to display.")] = 20,
    status_filter: Annotated[str, typer.Option(help="Filter by application status (e.g., 'applied', 'interview', 'rejected').")] = None
):
    """
    Displays all logged job applications with their current status.
    """
    console.print(f"\n[bold blue]📋 Viewing recent job applications[/bold blue]")
    logger.info(f"view_applications command initiated with limit: {limit}, status_filter: {status_filter}")

    try:
        # Get application logs from database
        console.print("🔍 Retrieving application logs from database...")
        application_logs = get_application_logs(user_profile_id=1, limit=limit)
        
        if not application_logs:
            console.print("[yellow]No application logs found in the database.[/yellow]")
            console.print("💡 Use 'log-application' to start tracking your job applications.")
            logger.info("No application logs found for user")
            return
        
        # Filter by status if specified
        if status_filter:
            application_logs = [app for app in application_logs if app.status.lower() == status_filter.lower()]
            if not application_logs:
                console.print(f"[yellow]No applications found with status '{status_filter}'.[/yellow]")
                return
        
        console.print(f"Found {len(application_logs)} applications to display...")
        
        # Display applications table
        table = Table(title=f"Job Applications Log ({len(application_logs)} applications)", show_lines=True)
        table.add_column("ID", style="dim", width=3, justify="right")
        table.add_column("Date", style="cyan", width=10)
        table.add_column("Job Title", style="magenta", min_width=20, max_width=25, overflow="ellipsis")
        table.add_column("Company", style="yellow", min_width=15, max_width=20, overflow="ellipsis")
        table.add_column("Status", style="green", width=12)
        table.add_column("Resume", style="blue", width=12, overflow="ellipsis")
        table.add_column("Notes", style="white", max_width=25, overflow="ellipsis")

        for app in application_logs:
            # Format date
            date_str = "N/A"
            if app.application_date:
                try:
                    date_str = app.application_date.strftime("%m-%d") if app.application_date else "N/A"
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Date formatting error: {e}")
                    date_str = str(app.application_date) if app.application_date else "N/A"
            
            # Format status with emoji
            status_display = str(app.status).title() if app.status else "Unknown"
            if app.status and app.status.lower() in ['applied', 'submitted']:
                status_display = f"📤 {status_display}"
            elif app.status and app.status.lower() in ['interview', 'screening']:
                status_display = f"📞 {status_display}"
            elif app.status and app.status.lower() in ['offer', 'accepted']:
                status_display = f"🎉 {status_display}"
            elif app.status and app.status.lower() in ['rejected', 'declined']:
                status_display = f"❌ {status_display}"
            else:
                status_display = f"📝 {status_display}"
            
            # Truncate long fields and ensure all are strings
            job_title = str(app.job_title)[:22] + "..." if app.job_title and len(str(app.job_title)) > 25 else str(app.job_title or "N/A")
            company = str(app.company_name)[:17] + "..." if app.company_name and len(str(app.company_name)) > 20 else str(app.company_name or "N/A")
            notes = str(app.notes)[:27] + "..." if app.notes and len(str(app.notes)) > 30 else str(app.notes or "")
            resume_name = os.path.basename(str(app.resume_version_used_path)) if app.resume_version_used_path else "N/A"
            
            table.add_row(
                str(app.internal_db_id) if app.internal_db_id else "N/A",
                str(date_str),
                str(job_title),
                str(company),
                str(status_display),
                str(resume_name),
                str(notes)
            )
        
        # Check if rows were actually added
        if not table.rows:
            console.print("[yellow]Data retrieved but no rows added to table. Check data processing.[/yellow]")
            logger.warning("Table has no rows despite having application data")
        else:
            console.print(table)
        
        # Display summary statistics
        status_counts = {}
        for app in application_logs:
            status = app.status.lower() if app.status else "unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
        
        console.print(f"\n[bold blue]📊 Application Summary:[/bold blue]")
        for status, count in sorted(status_counts.items()):
            console.print(f"  {status.title()}: {count}")
        
        # Show next steps
        console.print(f"\n💡 Application Management:")
        console.print("  • Update status: Use 'log-application' with same URL and new status")
        console.print("  • Add notes: Include notes when logging applications")
        console.print("  • Track follow-ups: Set reminders for application follow-ups")
        
        logger.info(f"Displayed {len(application_logs)} application logs to user")
        
    except Exception as e:
        logger.error(f"An unexpected error occurred during view_applications: {e}", exc_info=True)
        console.print(f"[bold red]Error retrieving applications: {e}[/bold red]")
        console.print("💡 This might be due to:")
        console.print("  • Database connection issues")
        console.print("  • Corrupted application data")
        raise typer.Exit(code=1)

@app.command()
def optimize_resume(
    resume_path: Annotated[str, typer.Option(help="Path to your resume file (.txt or .md format).")],
    job_id: Annotated[int, typer.Option(help="Database ID of the job to optimize resume for.")] = None,
    job_url: Annotated[str, typer.Option(help="URL of job to optimize for (alternative to job-id).")] = None,
    output_path: Annotated[str, typer.Option(help="Path to save optimization suggestions.")] = None
):
    """
    Optimizes your resume for a specific job using AI analysis.
    Provides detailed suggestions for improving ATS compatibility and relevance.
    """
    console.print(f"\n[bold blue]🔧 AI Resume Optimization[/bold blue]")
    logger.info(f"optimize_resume command: resume_path='{resume_path}', job_id={job_id}, job_url='{job_url}'")

    # Validate inputs
    if not job_id and not job_url:
        console.print("[bold red]❌ Either --job-id or --job-url must be provided.[/bold red]")
        console.print("💡 Use 'view-applications' to find job IDs or provide a job URL.")
        raise typer.Exit(code=1)

    # Check if Gemini API key is configured
    if not settings.GEMINI_API_KEY:
        console.print("[bold red]❌ GEMINI_API_KEY is not configured![/bold red]")
        console.print("Please add your Gemini API key to the .env file")
        logger.error("optimize_resume command failed: GEMINI_API_KEY not configured")
        raise typer.Exit(code=1)

    # Load resume file
    try:
        console.print(f"📄 Loading resume from: {resume_path}")
        if not os.path.exists(resume_path):
            console.print(f"[bold red]❌ Resume file not found: {resume_path}[/bold red]")
            raise typer.Exit(code=1)
        
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
        
        if not resume_text.strip():
            console.print("[bold red]❌ Resume file is empty.[/bold red]")
            raise typer.Exit(code=1)
            
        console.print(f"✅ Resume loaded ({len(resume_text)} characters)")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error loading resume: {e}[/bold red]")
        logger.error(f"Error loading resume file {resume_path}: {e}")
        raise typer.Exit(code=1)

    # Find job information
    job_info = None
    try:
        if job_id:
            console.print(f"🔍 Looking up job by ID: {job_id}")
            # Get job from database by ID
            all_jobs = get_all_jobs(limit=100)  # Get more jobs to search through
            job_info = next((job for job in all_jobs if job.internal_db_id == job_id), None)
            if not job_info:
                console.print(f"[bold red]❌ Job with ID {job_id} not found in database.[/bold red]")
                raise typer.Exit(code=1)
        elif job_url:
            console.print(f"🔍 Looking up job by URL: {job_url}")
            job_info = find_job_by_url(job_url)
            if not job_info:
                console.print(f"[bold red]❌ Job with URL {job_url} not found in database.[/bold red]")
                console.print("💡 Add the job to your database first using 'find-jobs' or 'log-application'")
                raise typer.Exit(code=1)
        
        console.print(f"✅ Found job: '{job_info.title}' at '{job_info.company_name}'")
        
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]❌ Error finding job information: {e}[/bold red]")
        logger.error(f"Error finding job: {e}")
        raise typer.Exit(code=1)

    # Generate optimization suggestions
    try:
        console.print("🤖 Generating AI-powered optimization suggestions...")
        gemini_service = GeminiService()
        
        suggestions = gemini_service.get_resume_optimization_suggestions(
            resume_text=resume_text,
            job_description=job_info.full_description_text or job_info.full_description_raw or "No description available",
            job_title=job_info.title
        )
        
        if not suggestions:
            console.print("[bold red]❌ Failed to generate optimization suggestions.[/bold red]")
            console.print("💡 This might be due to API issues or content filtering.")
            raise typer.Exit(code=1)
        
        # Display suggestions
        console.print(f"\n[bold green]✅ Resume Optimization Complete![/bold green]")
        console.print(f"[bold]Target Job:[/bold] {job_info.title} at {job_info.company_name}")
        console.print(f"[bold]Resume Analysis:[/bold] {os.path.basename(resume_path)}")
        
        # Create a panel for the suggestions
        from rich.panel import Panel
        from rich.markdown import Markdown
        
        suggestions_panel = Panel(
            Markdown(suggestions),
            title="🎯 AI Resume Optimization Suggestions",
            border_style="green"
        )
        console.print(suggestions_panel)
        
        # Save suggestions if output path provided
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Resume Optimization Suggestions\n\n")
                    f.write(f"**Target Job:** {job_info.title} at {job_info.company_name}\n")
                    f.write(f"**Resume File:** {resume_path}\n")
                    f.write(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(suggestions)
                console.print(f"\n💾 Suggestions saved to: {output_path}")
            except Exception as e:
                console.print(f"[yellow]⚠️ Could not save to {output_path}: {e}[/yellow]")
        
        # Show next steps
        console.print(f"\n💡 Next steps:")
        console.print(f"  • Review and implement the suggested changes")
        console.print(f"  • Update your resume based on the recommendations")
        console.print(f"  • Test ATS compatibility with the optimized resume")
        console.print(f"  • Use 'log-application' to track when you apply with the optimized resume")
        
        logger.info(f"Successfully generated resume optimization suggestions for job {job_info.internal_db_id}")
        
    except ValueError as ve:
        console.print(f"[bold red]Configuration Error: {ve}[/bold red]")
        logger.error(f"GeminiService initialization failed: {ve}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during resume optimization: {e}", exc_info=True)
        console.print(f"[bold red]Optimization Error: {e}[/bold red]")
        console.print("💡 This might be due to:")
        console.print("  • Network connectivity issues")
        console.print("  • Gemini API service problems")
        console.print("  • Invalid resume or job content")
        raise typer.Exit(code=1)

@app.command()
def smart_workflow(
    keywords: Annotated[str, typer.Option(help="Keywords for job search (e.g., 'Python Developer').")],
    target_role: Annotated[str, typer.Option(help="Your target role for AI analysis (e.g., 'Senior Python Developer').")],
    location: Annotated[str, typer.Option(help="Location preference (optional).")] = None,
    num_results: Annotated[int, typer.Option(help="Number of jobs to discover and analyze.")] = 5,
    interactive: Annotated[bool, typer.Option("--interactive", help="Run in interactive mode with prompts.")] = False
):
    """
    🚀 Intelligent end-to-end workflow: Discover jobs → AI analysis → Smart recommendations.
    Combines job discovery, AI relevance analysis, and actionable suggestions in one command.
    """
    if interactive:
        console.print(f"\n[bold blue]🤖 Starting Interactive Smart Workflow[/bold blue]")
        logger.info("smart_workflow command: starting interactive mode")
        
        try:
            orchestrator = AgentOrchestrator()
            orchestrator.interactive_workflow_prompt()
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Interactive workflow cancelled by user.[/yellow]")
            logger.info("Interactive workflow cancelled by user")
        except Exception as e:
            logger.error(f"Error during interactive workflow: {e}", exc_info=True)
            console.print(f"[bold red]Interactive workflow error: {e}[/bold red]")
            raise typer.Exit(code=1)
    else:
        console.print(f"\n[bold blue]🚀 Starting Smart Workflow[/bold blue]")
        console.print(f"Keywords: '{keywords}' | Target Role: '{target_role}' | Location: '{location or 'Any'}'")
        logger.info(f"smart_workflow command: keywords='{keywords}', target_role='{target_role}', location='{location}', num_results={num_results}")
        
        try:
            orchestrator = AgentOrchestrator()
            
            # Execute the discover and analyze workflow
            workflow_results = orchestrator.discover_and_analyze_workflow(
                keywords=keywords,
                location=location,
                num_results=num_results,
                target_role=target_role,
                auto_analyze=True
            )
            
            # Show smart application suggestions if we found high-relevance jobs
            high_relevance_jobs = workflow_results.get("high_relevance_jobs", [])
            if high_relevance_jobs:
                console.print(f"\n[bold green]🎯 Smart Application Recommendations[/bold green]")
                suggestions = orchestrator.smart_application_suggestions()
                
                if suggestions:
                    for i, suggestion in enumerate(suggestions[:5], 1):
                        console.print(f"{i}. {suggestion.get('action', 'No action available')}")
                        if suggestion.get('reason'):
                            console.print(f"   💡 {suggestion['reason']}")
                else:
                    console.print("💡 All high-relevance jobs have been applied to or no suggestions available")
                
                console.print(f"\n[bold cyan]📋 Recommended Next Steps:[/bold cyan]")
                console.print("• Use 'optimize-resume --job-id X' for top jobs")
                console.print("• Use 'log-application' when you apply")
                console.print("• Run 'view-applications' to track progress")
            
            # Summary
            total_errors = len(workflow_results.get("errors", []))
            if total_errors == 0:
                console.print(f"\n[bold green]✅ Smart workflow completed successfully![/bold green]")
            else:
                console.print(f"\n[bold yellow]⚠️ Workflow completed with {total_errors} issues. Check logs for details.[/bold yellow]")
            
            logger.info(f"Smart workflow completed: {workflow_results.get('jobs_discovered', 0)} discovered, {workflow_results.get('jobs_analyzed', 0)} analyzed")
            
        except Exception as e:
            logger.error(f"Error during smart workflow: {e}", exc_info=True)
            console.print(f"[bold red]Smart workflow error: {e}[/bold red]")
            console.print("💡 Try running individual commands (find-jobs, analyze-jobs) to isolate the issue")
            raise typer.Exit(code=1)

@app.command()
def find_jobs_multi(
    keywords: str = typer.Argument(help="Job search keywords"),
    sources: str = typer.Option("remote.co", "--sources", "-s", help="Comma-separated list of sources: remote.co,linkedin,indeed"),
    num_results: int = typer.Option(10, "--results", "-n", help="Number of results per source"),
    location: str = typer.Option(None, "--location", "-l", help="Job location filter")
):
    """
    🚀 PHASE 4.1: Multi-Site Job Discovery
    
    Search for jobs across multiple job boards simultaneously with intelligent deduplication.
    
    Examples:
    • find-jobs-multi "Python developer" --sources remote.co,indeed
    • find-jobs-multi "Data scientist" --sources remote.co,linkedin,indeed --results 5
    • find-jobs-multi "Frontend developer" --location "San Francisco"
    """
    import asyncio
    from app.services.scrapers import create_scraper_manager, get_available_scrapers
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from app.services.database_service import save_job_posting
    
    try:
        # Parse and validate sources
        requested_sources = [s.strip().lower() for s in sources.split(',')]
        available_scrapers = get_available_scrapers()
        
        # Validate sources
        invalid_sources = [s for s in requested_sources if s not in available_scrapers]
        if invalid_sources:
            console.print(f"[red]❌ Invalid sources: {', '.join(invalid_sources)}[/red]")
            console.print(f"Available sources: {', '.join(available_scrapers.keys())}")
            raise typer.Exit(1)
        
        # Display search configuration
        config_panel = Panel(
            f"🎯 **Keywords:** {keywords}\n"
            f"📍 **Location:** {location or 'Remote/Any'}\n"
            f"🌐 **Sources:** {', '.join(requested_sources)}\n"
            f"📊 **Results per source:** {num_results}",
            title="🚀 Multi-Site Job Search Configuration",
            title_align="left"
        )
        console.print(config_panel)
        
        # Show scraper information
        info_panels = []
        for source in requested_sources:
            scraper_info = available_scrapers[source]
            auth_status = "🔒 Auth Required" if scraper_info['authentication_required'] else "🔓 No Auth"
            reliability = f"📈 {scraper_info['reliability']} Reliability"
            
            panel = Panel(
                f"{scraper_info['description']}\n\n"
                f"{auth_status}\n"
                f"{reliability}",
                title=f"🌐 {scraper_info['name']}",
                title_align="left"
            )
            info_panels.append(panel)
        
        console.print(Columns(info_panels))
        
        # Create and configure scraper manager
        console.print("\n[yellow]⚙️ Initializing multi-site scraper...[/yellow]")
        scraper_manager = create_scraper_manager(enabled_sources=requested_sources)
        
        # Display enabled scrapers
        enabled = scraper_manager.get_enabled_sources()
        console.print(f"[green]✅ Enabled scrapers: {', '.join(enabled)}[/green]")
        
        # Run the multi-site search
        async def run_multi_search():
            console.print(f"\n[cyan]🔍 Searching across {len(requested_sources)} job boards...[/cyan]")
            
            try:
                result = await scraper_manager.search_all_sources(
                    keywords=keywords,
                    location=location,
                    num_results_per_source=num_results,
                    sources=requested_sources
                )
                
                return result
                
            except Exception as e:
                console.print(f"[red]❌ Multi-site search error: {e}[/red]")
                return None
            finally:
                # Cleanup
                await scraper_manager.cleanup_all()
        
        # Execute search
        search_result = asyncio.run(run_multi_search())
        
        if not search_result or not search_result.all_jobs:
            console.print("[yellow]⚠️ No jobs found across any sources[/yellow]")
            return
        
        # Display results summary
        summary_panel = Panel(
            f"🎯 **Total Jobs Found:** {search_result.total_found}\n"
            f"🔄 **Duplicates Removed:** {search_result.duplicates_removed}\n"
            f"⏱️ **Execution Time:** {search_result.execution_time:.2f}s\n"
            f"✅ **Successful Sources:** {', '.join(search_result.successful_sources)}\n"
            f"❌ **Failed Sources:** {', '.join(search_result.failed_sources) if search_result.failed_sources else 'None'}",
            title="📊 Multi-Site Search Results",
            title_align="left"
        )
        console.print(summary_panel)
        
        # Display per-source breakdown
        if search_result.results_by_source:
            breakdown_table = Table(title="📈 Results Breakdown by Source")
            breakdown_table.add_column("Source", style="cyan")
            breakdown_table.add_column("Status", style="green")
            breakdown_table.add_column("Jobs Found", style="yellow")
            breakdown_table.add_column("Execution Time", style="blue")
            breakdown_table.add_column("Notes", style="dim")
            
            for source, result in search_result.results_by_source.items():
                status = "✅ Success" if result.success else "❌ Failed"
                jobs_count = str(len(result.jobs))
                exec_time = f"{result.execution_time:.2f}s"
                notes = result.error_message if result.error_message else "—"
                
                breakdown_table.add_row(source, status, jobs_count, exec_time, notes)
            
            console.print(breakdown_table)
        
        # Display job results
        if search_result.all_jobs:
            jobs_table = Table(title=f"🎯 Found {len(search_result.all_jobs)} Unique Jobs")
            jobs_table.add_column("Title", style="bright_blue", width=30)
            jobs_table.add_column("Company", style="green", width=20)
            jobs_table.add_column("Location", style="yellow", width=15)
            jobs_table.add_column("Source", style="cyan", width=12)
            jobs_table.add_column("URL", style="dim", width=25)
            
            for job in search_result.all_jobs[:20]:  # Limit display
                # Truncate long fields
                title = job.title[:27] + "..." if len(job.title) > 30 else job.title
                company = job.company_name[:17] + "..." if len(job.company_name) > 20 else job.company_name
                location = job.location_text[:12] + "..." if len(job.location_text) > 15 else job.location_text
                # Convert HttpUrl to string before slicing
                url_str = str(job.job_url)
                url = url_str[:22] + "..." if len(url_str) > 25 else url_str
                
                jobs_table.add_row(title, company, location, job.source_platform, url)
            
            console.print(jobs_table)
            
            if len(search_result.all_jobs) > 20:
                console.print(f"[dim]... and {len(search_result.all_jobs) - 20} more jobs[/dim]")
        
        # Save jobs to database
        console.print(f"\n[cyan]💾 Saving {len(search_result.all_jobs)} jobs to database...[/cyan]")
        saved_count = 0
        for job in search_result.all_jobs:
            try:
                save_job_posting(job)
                saved_count += 1
            except Exception as e:
                console.print(f"[yellow]⚠️ Failed to save job {job.title}: {e}[/yellow]")
        
        console.print(f"[green]✅ Successfully saved {saved_count} jobs to database![/green]")
        
        # Show next steps
        next_steps_panel = Panel(
            "🎯 **Analyze Jobs:** `python main.py analyze-jobs`\n"
            "📝 **Log Application:** `python main.py log-application <job-url>`\n"
            "🔍 **View Applications:** `python main.py view-applications`\n"
            "🚀 **Smart Workflow:** `python main.py smart-workflow`",
            title="🚀 Next Steps",
            title_align="left"
        )
        console.print(next_steps_panel)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]🛑 Search cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error in multi-site job search: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="linkedin-session-info")
def linkedin_session_info():
    """
    📋 Display LinkedIn session information and status.
    Shows session file location, age, and validity.
    """
    import os
    import json
    from rich.panel import Panel
    
    console.print(f"\n[bold blue]📋 LinkedIn Session Information[/bold blue]")
    
    session_file = "linkedin_session.json"
    session_path = os.path.join(os.getcwd(), session_file)
    
    try:
        if not os.path.exists(session_path):
            panel = Panel(
                "❌ **No session file found**\n\n"
                f"Expected location: `{session_path}`\n"
                "Run LinkedIn scraping once to create a session.",
                title="Session Status: Not Found",
                title_align="left"
            )
            console.print(panel)
            return
        
        # Load and analyze session
        with open(session_path, 'r') as f:
            session_data = json.load(f)
        
        # Calculate session age
        if 'timestamp' in session_data:
            session_time = datetime.fromisoformat(session_data['timestamp'])
            age_days = (datetime.now() - session_time).days
            age_hours = ((datetime.now() - session_time).seconds // 3600)
            
            if age_days > 0:
                age_str = f"{age_days} days old"
            else:
                age_str = f"{age_hours} hours old"
        else:
            age_str = "Unknown age"
        
        # Session validity
        is_valid = age_days <= 7 if 'timestamp' in session_data else False
        validity_status = "✅ Valid" if is_valid else "⚠️ Expired"
        
        # Cookie count
        cookie_count = len(session_data.get('cookies', []))
        
        # Create info panel
        panel_content = (
            f"📁 **File:** `{session_path}`\n"
            f"🕒 **Age:** {age_str}\n"
            f"✅ **Status:** {validity_status}\n"
            f"🍪 **Cookies:** {cookie_count} stored\n"
            f"🌐 **User Agent:** {session_data.get('user_agent', 'Not stored')[:50]}...\n"
            f"🔗 **Last URL:** {session_data.get('url', 'Not stored')}"
        )
        
        if is_valid:
            panel = Panel(panel_content, title="Session Status: Active", title_align="left", border_style="green")
        else:
            panel_content += "\n\n⚠️ Session will require fresh login on next use."
            panel = Panel(panel_content, title="Session Status: Expired", title_align="left", border_style="yellow")
        
        console.print(panel)
        
        # Show management options
        console.print(f"\n💡 **Session Management:**")
        console.print("• `python main.py linkedin-session-refresh` - Force new login")
        console.print("• `python main.py linkedin-session-clear` - Clear session file")
        
    except Exception as e:
        console.print(f"[red]❌ Error reading session file: {e}[/red]")

@app.command(name="linkedin-session-refresh")
def linkedin_session_refresh():
    """
    🔄 Force refresh LinkedIn session by clearing current session and prompting for new login.
    """
    import os
    from rich.panel import Panel
    
    console.print(f"\n[bold blue]🔄 Refreshing LinkedIn Session[/bold blue]")
    
    session_file = "linkedin_session.json"
    session_path = os.path.join(os.getcwd(), session_file)
    
    try:
        # Clear existing session
        if os.path.exists(session_path):
            os.remove(session_path)
            console.print(f"✅ Cleared existing session file")
        else:
            console.print(f"ℹ️ No existing session file found")
        
        # Inform user about next steps
        panel = Panel(
            "🔄 **Session Cleared Successfully**\n\n"
            "Next LinkedIn scraping command will prompt for fresh login.\n"
            "Your new session will be automatically saved after successful login.\n\n"
            "**Try this command:**\n"
            "`python main.py find-jobs-multi \"Python Developer\" --sources linkedin --results 3`",
            title="Session Refresh Complete",
            title_align="left",
            border_style="green"
        )
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]❌ Error refreshing session: {e}[/red]")
        raise typer.Exit(1)

@app.command(name="linkedin-session-clear")  
def linkedin_session_clear():
    """Clear saved LinkedIn session data (forces re-authentication)"""
    console.print("\n[bold blue]🧹 Clearing LinkedIn Session Data[/bold blue]")
    
    try:
        from app.services.linkedin_scraper_service import clear_session_data
        
        success = clear_session_data()
        
        if success:
            console.print("[green]✅ LinkedIn session data cleared successfully[/green]")
            console.print("   Next LinkedIn operation will require fresh login")
            logger.info("LinkedIn session data cleared")
        else:
            console.print("[yellow]⚠️ No session data found to clear[/yellow]")
            logger.info("No LinkedIn session data found to clear")
            
    except ImportError:
        console.print("[red]❌ LinkedIn scraper service not available[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"Error clearing LinkedIn session: {e}")
        console.print(f"[red]❌ Error clearing session: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def ensure_semantic_schema():
    """
    🔧 Ensures database schema supports semantic analysis features.
    Run this once before using semantic analysis commands.
    """
    console.print("\n[bold blue]🔧 Ensuring Database Schema for Semantic Analysis[/bold blue]")
    logger.info("ensure_semantic_schema command initiated")
    
    try:
        console.print("📋 Checking and updating database schema...")
        add_embedding_columns_if_not_exist()
        console.print("[bold green]✅ Database schema ready for semantic analysis![/bold green]")
        logger.info("Database schema successfully updated for semantic analysis")
    except Exception as e:
        console.print(f"[bold red]❌ Error updating database schema: {e}[/bold red]")
        logger.error(f"Database schema update failed: {e}", exc_info=True)
        raise typer.Exit(code=1)

@app.command()
def semantic_analysis(
    target_role: Annotated[str, typer.Option(help="Your target role for semantic matching analysis.")] = "Software Engineer",
    limit: Annotated[int, typer.Option(help="Maximum number of jobs to analyze.")] = 20,
    min_score: Annotated[float, typer.Option(help="Minimum combined score threshold.")] = 3.0,
    model: Annotated[str, typer.Option(help="Embedding model to use.")] = "all-MiniLM-L6-v2",
    update_db: Annotated[bool, typer.Option(help="Update database with semantic scores.")] = True
):
    """
    🧠 Phase 5.1: Advanced Semantic Analysis & Intelligent Job Matching
    
    Performs semantic analysis on stored jobs using sentence-transformers embeddings
    to provide intelligent job matching with combined AI + semantic scoring.
    """
    console.print(f"\n[bold blue]🧠 Phase 5.1: Semantic Analysis & Intelligent Job Matching[/bold blue]")
    console.print(f"🎯 Target Role: {target_role}")
    console.print(f"📊 Model: {model}")
    console.print(f"🔢 Analyzing up to {limit} jobs with min score {min_score}")
    logger.info(f"semantic_analysis command: target_role='{target_role}', limit={limit}, min_score={min_score}, model={model}")

    async def run_semantic_analysis():
        try:
            # Initialize services
            console.print("🔧 Initializing semantic analysis service...")
            service = get_semantic_analysis_service(model)
            
            # Get jobs from database
            console.print("📥 Retrieving jobs from database...")
            all_jobs = get_all_jobs(limit=limit * 2)  # Get more than limit to ensure good results
            
            if not all_jobs:
                console.print("[yellow]⚠️ No jobs found in database.[/yellow]")
                console.print("💡 Try running 'find-jobs-multi' or 'smart-workflow' first to populate the database.")
                return
            
            console.print(f"📊 Found {len(all_jobs)} jobs in database")
            
            # Create custom user profile
            custom_profile = {
                "target_role": target_role,
                "experience_years": 5,
                "skills": ["Python", "JavaScript", "React", "FastAPI", "PostgreSQL", "AWS"],
                "preferred_locations": ["Remote", "San Francisco", "New York"],
                "resume_text": f"""
                Experienced {target_role} with strong technical skills and industry experience.
                Skilled in modern development practices, cloud technologies, and collaborative development.
                Looking for challenging opportunities that align with career growth and learning objectives.
                """
            }
            
            # Perform batch semantic analysis
            console.print("🔍 Performing semantic analysis...")
            with console.status("[bold green]Generating embeddings and calculating semantic similarities..."):
                analyzed_jobs = await service.batch_analyze_jobs(all_jobs, custom_profile)
            
            console.print(f"✅ Analyzed {len(analyzed_jobs)} jobs")
            
            # Get top matches
            top_matches = service.get_top_matches(analyzed_jobs, limit=limit, min_combined_score=min_score)
            
            if not top_matches:
                console.print(f"[yellow]⚠️ No jobs found with combined score >= {min_score}[/yellow]")
                console.print("💡 Try lowering the min-score threshold or expanding your search criteria.")
                return
            
            # Display results table
            table = Table(title=f"🏆 Top {len(top_matches)} Semantic Job Matches")
            table.add_column("Rank", style="dim", width=4)
            table.add_column("Job Title", style="cyan", min_width=25)
            table.add_column("Company", style="magenta", min_width=18)
            table.add_column("Combined Score", style="green", width=14)
            table.add_column("Semantic Sim.", style="yellow", width=12)
            table.add_column("AI Relevance", style="blue", width=12)
            table.add_column("Location", style="white", min_width=15)
            table.add_column("Source", style="dim", width=12)

            for i, job in enumerate(top_matches, 1):
                semantic_score = f"{job.semantic_similarity_score:.3f}" if job.semantic_similarity_score else "N/A"
                ai_score = f"{job.relevance_score:.1f}" if job.relevance_score else "N/A"
                combined_score = f"{job.combined_match_score:.2f}" if job.combined_match_score else "N/A"
                
                table.add_row(
                    str(i),
                    job.title[:24] + "..." if len(job.title) > 24 else job.title,
                    job.company_name[:17] + "..." if len(job.company_name) > 17 else job.company_name,
                    combined_score,
                    semantic_score,
                    ai_score,
                    job.location_text[:14] + "..." if job.location_text and len(job.location_text) > 14 else job.location_text or "N/A",
                    job.source_platform[:11] if job.source_platform else "N/A"
                )
            
            console.print(table)
            
            # Display analysis statistics
            stats = service.get_analysis_stats(analyzed_jobs)
            console.print(f"\n📊 [bold]Analysis Statistics:[/bold]")
            console.print(f"   Total jobs analyzed: {stats['total_jobs']}")
            console.print(f"   Jobs with embeddings: {stats['jobs_with_embeddings']} ({stats['embedding_coverage']:.1%})")
            console.print(f"   Avg semantic similarity: {stats.get('avg_semantic_similarity', 0):.3f}")
            console.print(f"   Avg combined score: {stats.get('avg_combined_score', 0):.2f}")
            console.print(f"   Top matches found: {len(top_matches)}")
            
            # Show sample insights for top job
            if top_matches:
                top_job = top_matches[0]
                console.print(f"\n🎯 [bold]Top Match Insights:[/bold]")
                console.print(f"   Job: {top_job.title} at {top_job.company_name}")
                console.print(f"   Combined Score: {top_job.combined_match_score:.2f}/5.0")
                console.print(f"   Semantic Match: {top_job.semantic_similarity_score:.3f} (cosine similarity)")
                console.print(f"   AI Relevance: {top_job.relevance_score}/5.0")
            
            # Summary and next steps
            console.print(f"\n🎉 [bold green]Semantic Analysis Complete![/bold green]")
            console.print("💡 Next steps:")
            console.print("  • Review top matches for application opportunities")
            console.print("  • Use 'optimize-resume' for specific job requirements")
            console.print("  • Run 'log-application' to track your applications")
            console.print("  • Use semantic search with natural language queries")
            
            logger.info(f"Semantic analysis completed: {len(top_matches)} top matches found")
            
        except Exception as e:
            logger.error(f"Error in semantic analysis: {e}", exc_info=True)
            console.print(f"[bold red]❌ Error in semantic analysis: {e}[/bold red]")
            raise typer.Exit(1)
    
    # Run the async analysis
    asyncio.run(run_semantic_analysis())

@app.command()
def semantic_search(
    query: str = typer.Argument(help="Natural language search query"),
    limit: Annotated[int, typer.Option(help="Maximum number of results to return.")] = 10,
    model: Annotated[str, typer.Option(help="Embedding model to use.")] = "all-MiniLM-L6-v2"
):
    """
    🔍 Phase 5.1: Semantic Job Search
    
    Search jobs using natural language queries with semantic similarity matching.
    Example: "Python backend development with cloud experience"
    """
    console.print(f"\n[bold blue]🔍 Phase 5.1: Semantic Job Search[/bold blue]")
    console.print(f"🔎 Query: '{query}'")
    console.print(f"📊 Model: {model}")
    logger.info(f"semantic_search command: query='{query}', limit={limit}")

    async def run_semantic_search():
        try:
            # Initialize semantic analysis service
            service = get_semantic_analysis_service(model)
            
            # Perform semantic search
            console.print("🔍 Searching jobs with semantic similarity...")
            results = await service.semantic_job_search(query, limit=limit)
            
            if not results:
                console.print("[yellow]⚠️ No jobs found matching your search query.[/yellow]")
                console.print("💡 Try different keywords or run 'semantic-analysis' first to ensure jobs have embeddings.")
                return
            
            # Display results table
            table = Table(title=f"🔍 Semantic Search Results: '{query}'")
            table.add_column("Rank", style="dim", width=4)
            table.add_column("Job Title", style="cyan", min_width=25)
            table.add_column("Company", style="magenta", min_width=18)
            table.add_column("Similarity", style="green", width=10)
            table.add_column("Combined Score", style="yellow", width=14)
            table.add_column("Location", style="white", min_width=15)
            table.add_column("Source", style="dim", width=12)

            for i, job in enumerate(results, 1):
                # Calculate similarity with query
                similarity = 0.0
                if job.description_embedding:
                    job_embedding = service.embedding_service.embedding_from_json(job.description_embedding)
                    query_embedding = service.embedding_service.encode_text(query)
                    similarity = service.embedding_service.calculate_similarity(query_embedding, job_embedding)
                
                combined_score = f"{job.combined_match_score:.2f}" if job.combined_match_score else "N/A"
                
                table.add_row(
                    str(i),
                    job.title[:24] + "..." if len(job.title) > 24 else job.title,
                    job.company_name[:17] + "..." if len(job.company_name) > 17 else job.company_name,
                    f"{similarity:.3f}",
                    combined_score,
                    job.location_text[:14] + "..." if job.location_text and len(job.location_text) > 14 else job.location_text or "N/A",
                    job.source_platform[:11] if job.source_platform else "N/A"
                )
            
            console.print(table)
            
            # Show top result details
            if results:
                top_result = results[0]
                console.print(f"\n🎯 [bold]Top Result:[/bold]")
                console.print(f"   Title: {top_result.title}")
                console.print(f"   Company: {top_result.company_name}")
                console.print(f"   Location: {top_result.location_text}")
                if top_result.salary_min and top_result.salary_max:
                    console.print(f"   Salary: ${top_result.salary_min:,.0f} - ${top_result.salary_max:,.0f}")
                if top_result.job_url:
                    console.print(f"   URL: {top_result.job_url}")
            
            console.print(f"\n✅ Found {len(results)} semantically similar jobs")
            logger.info(f"Semantic search completed: {len(results)} results found")
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}", exc_info=True)
            console.print(f"[bold red]❌ Error in semantic search: {e}[/bold red]")
            raise typer.Exit(1)
    
    # Run the async search
    asyncio.run(run_semantic_search())

@app.command()
def create_profile(
    profile_name: str = typer.Argument(help="Name for this profile (e.g., 'senior_python_dev')"),
    full_name: Annotated[str, typer.Option(help="Your full name")] = None,
    email: Annotated[str, typer.Option(help="Your email address")] = None,
    phone: Annotated[str, typer.Option(help="Your phone number")] = None,
    linkedin_url: Annotated[str, typer.Option(help="Your LinkedIn URL")] = None,
    github_url: Annotated[str, typer.Option(help="Your GitHub URL")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", help="Create profile interactively")] = False
):
    """
    📝 Phase 4.2: Create User Profile for Application Automation
    
    Creates a comprehensive user profile for automated job applications.
    """
    console.print(f"\n[bold blue]📝 Phase 4.2: Creating User Profile '{profile_name}'[/bold blue]")
    
    try:
        if interactive:
            # Interactive profile creation
            console.print("🔍 Interactive Profile Creation")
            console.print("Please provide the following information (press Enter to skip optional fields):")
            
            if not full_name:
                full_name = typer.prompt("Full Name", default="")
            if not email:
                email = typer.prompt("Email Address", default="")
            if not phone:
                phone = typer.prompt("Phone Number", default="")
            if not linkedin_url:
                linkedin_url = typer.prompt("LinkedIn URL", default="")
            if not github_url:
                github_url = typer.prompt("GitHub URL", default="")
            
            # Additional fields
            summary = typer.prompt("Professional Summary", default="")
            target_roles = typer.prompt("Target Roles (comma-separated)", default="")
            preferred_locations = typer.prompt("Preferred Locations (comma-separated)", default="Remote")
            years_experience = typer.prompt("Years of Experience", type=int, default=0)
        else:
            summary = ""
            target_roles = ""
            preferred_locations = "Remote"
            years_experience = 0
        
        # Create UserProfile instance
        profile_data = {
            "profile_name": profile_name,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "linkedin_url": linkedin_url,
            "github_url": github_url,
            "summary_statement": summary,
            "target_roles": target_roles.split(",") if target_roles else [],
            "preferred_locations": preferred_locations.split(",") if preferred_locations else ["Remote"],
        }
        
        # Remove None values
        profile_data = {k: v for k, v in profile_data.items() if v}
        
        # Create profile
        user_profile = UserProfile(**profile_data)
        
        # Save profile to file
        profile_dir = "data/user_profiles"
        os.makedirs(profile_dir, exist_ok=True)
        profile_path = f"{profile_dir}/{profile_name}.json"
        
        with open(profile_path, 'w') as f:
            f.write(user_profile.model_dump_json(indent=2))
        
        console.print(f"✅ Profile '{profile_name}' created successfully!")
        console.print(f"📁 Saved to: {profile_path}")
        
        # Display profile summary
        table = Table(title=f"👤 Profile: {profile_name}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Full Name", user_profile.full_name or "Not set")
        table.add_row("Email", str(user_profile.email) if user_profile.email else "Not set")
        table.add_row("Phone", user_profile.phone or "Not set")
        table.add_row("LinkedIn", str(user_profile.linkedin_url) if user_profile.linkedin_url else "Not set")
        table.add_row("GitHub", str(user_profile.github_url) if user_profile.github_url else "Not set")
        table.add_row("Target Roles", ", ".join(user_profile.target_roles[:2]) if user_profile.target_roles else "Not set")
        
        console.print(table)
        
        console.print("\n💡 Next steps:")
        console.print("  • Use 'apply-to-job' command to apply to jobs with this profile")
        console.print("  • Edit the profile file directly for more detailed customization")
        console.print("  • Add work experience and education details to the JSON file")
        
        logger.info(f"Created user profile: {profile_name}")
        
    except Exception as e:
        logger.error(f"Error creating profile: {e}", exc_info=True)
        console.print(f"[bold red]❌ Error creating profile: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def apply_to_job(
    job_id: Annotated[int, typer.Option(help="Database ID of the job to apply to")] = None,
    job_url: Annotated[str, typer.Option(help="URL of the job to apply to (alternative to job-id)")] = None,
    profile_name: Annotated[str, typer.Option(help="Name of user profile to use for application")] = "default",
    headless: Annotated[bool, typer.Option("--headless", help="Run browser in headless mode")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Test form detection without filling")] = False
):
    """
    🚀 Phase 4.2: Automated Job Application with Form Filling
    
    Automatically navigates to job application page, fills forms with profile data,
    and provides Human-in-the-Loop review before submission.
    """
    console.print(f"\n[bold blue]🚀 Phase 4.2: Automated Job Application[/bold blue]")
    
    if not job_id and not job_url:
        console.print("[bold red]❌ Error: Must provide either --job-id or --job-url[/bold red]")
        raise typer.Exit(1)
    
    try:
        # Load job from database
        job = None
        if job_id:
            # Get job by ID
            all_jobs = get_all_jobs(limit=1000)  # Get a large number to find by ID
            job = next((j for j in all_jobs if j.internal_db_id == job_id), None)
            if not job:
                console.print(f"[bold red]❌ Job with ID {job_id} not found in database[/bold red]")
                raise typer.Exit(1)
        elif job_url:
            # Find job by URL
            job = find_job_by_url(job_url)
            if not job:
                console.print(f"[bold yellow]⚠️ Job not found in database, creating temporary job object[/bold yellow]")
                # Create temporary job object for URL
                job = JobPosting(
                    id_on_platform="temp",
                    source_platform="manual",
                    job_url=job_url,
                    title="Manual Application",
                    company_name="Unknown Company",
                    location="Unknown Location"
                )
        
        console.print(f"📋 Job: {job.title} at {job.company_name}")
        console.print(f"🔗 URL: {job.job_url}")
        
        # Load user profile
        profile_path = f"data/user_profiles/{profile_name}.json"
        if not os.path.exists(profile_path):
            console.print(f"[bold red]❌ Profile '{profile_name}' not found at {profile_path}[/bold red]")
            console.print("💡 Create a profile first using: create-profile")
            raise typer.Exit(1)
        
        with open(profile_path, 'r') as f:
            profile_data = f.read()
        
        user_profile = UserProfile.model_validate_json(profile_data)
        console.print(f"👤 Using profile: {user_profile.profile_name}")
        console.print(f"📧 Email: {user_profile.email}")
        
        # Confirm action with user
        hitl_service = get_hitl_service()
        if not hitl_service.confirm_action(
            f"Apply to {job.title} at {job.company_name}",
            context={
                "Job URL": str(job.job_url),
                "Profile": user_profile.profile_name,
                "Email": str(user_profile.email) if user_profile.email else "None",
                "Mode": "Dry Run" if dry_run else "Live Application"
            },
            default_response=False
        ):
            console.print("❌ Application cancelled by user")
            return
        
        # Initialize form filler service
        console.print("🔧 Initializing browser automation...")
        form_filler = get_form_filler_service(headless=headless)
        
        # Run the application process
        async def run_application():
            try:
                if dry_run:
                    console.print("🧪 [bold yellow]DRY RUN MODE - No actual application will be submitted[/bold yellow]")
                
                # Navigate to application page
                console.print("🌐 Navigating to job application page...")
                if not await form_filler.navigate_to_application(str(job.job_url)):
                    console.print("[bold red]❌ Failed to navigate to application page[/bold red]")
                    return
                
                # Detect form fields
                console.print("🔍 Detecting form fields...")
                detected_fields = await form_filler.detect_form_fields()
                
                if not detected_fields:
                    console.print("[bold yellow]⚠️ No form fields detected on this page[/bold yellow]")
                    console.print("💡 This might be because:")
                    console.print("  • The page doesn't have an application form")
                    console.print("  • The form uses non-standard field structures")
                    console.print("  • You need to click an 'Apply' button first")
                    return
                
                console.print(f"✅ Detected {len(detected_fields)} field types:")
                for field_type, selectors in detected_fields.items():
                    console.print(f"  • {field_type}: {len(selectors)} selector(s)")
                
                if dry_run:
                    console.print("🧪 [bold yellow]DRY RUN COMPLETE - Form fields detected successfully[/bold yellow]")
                    await form_filler.take_screenshot("dry_run_detection.png")
                    return
                
                # Fill form fields
                console.print("✏️ Filling form fields with profile data...")
                fill_results = await form_filler.fill_form_fields(user_profile, detected_fields)
                
                successful_fills = sum(fill_results.values())
                total_fields = len(fill_results)
                console.print(f"📝 Filled {successful_fills}/{total_fields} fields successfully")
                
                # Take screenshot for review
                screenshot_path = await form_filler.take_screenshot()
                console.print(f"📸 Screenshot saved: {screenshot_path}")
                
                # Human review and submission
                console.print("👀 Starting Human-in-the-Loop review...")
                if await form_filler.human_review_and_submit(user_profile, job):
                    # Log successful application
                    try:
                        app_log_id = save_application_log(
                            job_url=str(job.job_url),
                            resume_path="",  # Could be enhanced to include resume
                            status="Applied",
                            notes=f"Automated application via form filler. Filled {successful_fills}/{total_fields} fields.",
                            job_title=job.title,
                            company_name=job.company_name
                        )
                        console.print(f"📊 Application logged with ID: {app_log_id}")
                    except Exception as e:
                        logger.warning(f"Failed to log application: {e}")
                    
                    console.print("🎉 [bold green]Application submitted successfully![/bold green]")
                else:
                    console.print("❌ Application was not submitted")
                
            except Exception as e:
                logger.error(f"Error during application process: {e}", exc_info=True)
                console.print(f"[bold red]❌ Error during application: {e}[/bold red]")
            finally:
                # Clean up browser
                await form_filler.close_browser()
        
        # Run the async application process
        asyncio.run(run_application())
        
        console.print("\n💡 Tips for future applications:")
        console.print("  • Use --dry-run to test form detection first")
        console.print("  • Create multiple profiles for different job types")
        console.print("  • Check screenshots to verify form filling accuracy")
        console.print("  • Use 'view-applications' to track your application status")
        
        logger.info(f"Application process completed for job: {job.title}")
        
    except Exception as e:
        logger.error(f"Error in apply_to_job: {e}", exc_info=True)
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def list_profiles():
    """
    📋 Phase 4.2: List Available User Profiles
    
    Shows all available user profiles for job applications.
    """
    console.print(f"\n[bold blue]📋 Available User Profiles[/bold blue]")
    
    try:
        profile_dir = "data/user_profiles"
        if not os.path.exists(profile_dir):
            console.print("[yellow]⚠️ No profiles directory found[/yellow]")
            console.print("💡 Create your first profile with: create-profile")
            return
        
        profile_files = [f for f in os.listdir(profile_dir) if f.endswith('.json')]
        
        if not profile_files:
            console.print("[yellow]⚠️ No profiles found[/yellow]")
            console.print("💡 Create your first profile with: create-profile")
            return
        
        console.print(f"Found {len(profile_files)} profile(s):")
        
        table = Table(title="👤 User Profiles")
        table.add_column("Profile Name", style="cyan")
        table.add_column("Full Name", style="white")
        table.add_column("Email", style="yellow")
        table.add_column("Target Roles", style="green")
        table.add_column("Created", style="dim")
        
        for profile_file in profile_files:
            try:
                profile_path = os.path.join(profile_dir, profile_file)
                with open(profile_path, 'r') as f:
                    profile_data = f.read()
                
                profile = UserProfile.model_validate_json(profile_data)
                
                # Get file creation time
                created_time = datetime.fromtimestamp(os.path.getctime(profile_path))
                
                table.add_row(
                    profile.profile_name,
                    profile.full_name or "Not set",
                    str(profile.email) if profile.email else "Not set",
                    ", ".join(profile.target_roles[:2]) if profile.target_roles else "Not set",
                    created_time.strftime("%Y-%m-%d")
                )
                
            except Exception as e:
                logger.warning(f"Error loading profile {profile_file}: {e}")
                table.add_row(
                    profile_file.replace('.json', ''),
                    "Error loading",
                    "Error loading",
                    "Error loading",
                    "Unknown"
                )
        
        console.print(table)
        
        console.print("\n💡 Commands:")
        console.print("  • apply-to-job --profile-name <name> - Use profile for job application")
        console.print("  • create-profile <name> - Create new profile")
        console.print("  • Edit profile files directly for detailed customization")
        
    except Exception as e:
        logger.error(f"Error listing profiles: {e}", exc_info=True)
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def test_form_detection(
    url: str = typer.Argument(help="URL to test form detection on"),
    headless: Annotated[bool, typer.Option("--headless", help="Run browser in headless mode")] = False
):
    """
    🧪 Phase 4.2: Test Form Detection
    
    Test the form field detection capabilities on any URL.
    Useful for debugging and improving form filling accuracy.
    """
    console.print(f"\n[bold blue]🧪 Phase 4.2: Testing Form Detection[/bold blue]")
    console.print(f"🔗 URL: {url}")
    
    try:
        # Initialize form filler service
        form_filler = get_form_filler_service(headless=headless)
        
        async def run_test():
            try:
                # Navigate to the page
                console.print("🌐 Navigating to page...")
                if not await form_filler.navigate_to_application(url):
                    console.print("[bold red]❌ Failed to navigate to page[/bold red]")
                    return
                
                # Detect form fields
                console.print("🔍 Detecting form fields...")
                detected_fields = await form_filler.detect_form_fields()
                
                if not detected_fields:
                    console.print("[bold yellow]⚠️ No form fields detected[/bold yellow]")
                    await form_filler.take_screenshot("no_fields_detected.png")
                    return
                
                # Display detected fields
                table = Table(title="🔍 Detected Form Fields")
                table.add_column("Field Type", style="cyan")
                table.add_column("Selectors Found", style="yellow")
                table.add_column("Count", style="green")
                
                total_selectors = 0
                for field_type, selectors in detected_fields.items():
                    table.add_row(
                        field_type,
                        ", ".join(selectors[:3]) + ("..." if len(selectors) > 3 else ""),
                        str(len(selectors))
                    )
                    total_selectors += len(selectors)
                
                console.print(table)
                console.print(f"✅ Total: {len(detected_fields)} field types, {total_selectors} selectors")
                
                # Take screenshot
                screenshot_path = await form_filler.take_screenshot("form_detection_test.png")
                console.print(f"📸 Screenshot saved: {screenshot_path}")
                
                console.print("\n💡 Field Detection Tips:")
                console.print("  • High selector count indicates multiple similar fields")
                console.print("  • Missing expected fields suggest field mapping improvements needed")
                console.print("  • Use screenshots to verify detection accuracy")
                
            except Exception as e:
                logger.error(f"Error during form detection test: {e}", exc_info=True)
                console.print(f"[bold red]❌ Error: {e}[/bold red]")
            finally:
                await form_filler.close_browser()
        
        # Run the async test
        asyncio.run(run_test())
        
    except Exception as e:
        logger.error(f"Error in test_form_detection: {e}", exc_info=True)
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)

@app.command()
def launch_browser():
    """
    🌐 Launch the Suna-inspired browser interface for real-time job search visualization
    
    This command starts a web server that provides:
    - Real-time browser automation viewing
    - Live task progress tracking  
    - Visual feedback during job scraping
    - Screenshots and browser state monitoring
    
    The interface will be available at http://localhost:8080
    """
    console.print("\n🚀 [bold blue]Launching Suna-Inspired Browser Interface[/bold blue]")
    
    try:
        # Check if required dependencies are installed
        try:
            import fastapi
            import uvicorn
            import websockets
        except ImportError as e:
            console.print(f"❌ [bold red]Missing dependency:[/bold red] {e}")
            console.print("\n📦 [yellow]Please install additional dependencies:[/yellow]")
            console.print("   [cyan]pip install fastapi uvicorn websockets[/cyan]")
            return
        
        # Import and run the browser interface launcher
        import subprocess
        import sys
        from pathlib import Path
        
        launcher_script = Path(__file__).parent / "launch_browser_interface.py"
        
        if not launcher_script.exists():
            console.print("❌ [bold red]Browser interface launcher not found[/bold red]")
            return
        
        console.print("🌐 [green]Starting browser interface server...[/green]")
        console.print("💡 [yellow]Open your browser and go to:[/yellow] [link]http://localhost:8080[/link]")
        console.print("🔄 [dim]Press Ctrl+C to stop the service[/dim]\n")
        
        # Launch the browser interface
        subprocess.run([sys.executable, str(launcher_script)], check=True)
        
    except KeyboardInterrupt:
        console.print("\n🛑 [yellow]Browser interface stopped by user[/yellow]")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ [bold red]Failed to start browser interface:[/bold red] {e}")
    except Exception as e:
        console.print(f"❌ [bold red]Error:[/bold red] {e}")

@app.command()
def setup_profile():
    """
    🤖 Create or update your job application profile for automated applications
    
    This command sets up your personal profile with contact information, resume,
    and preferences for automated job applications across multiple platforms.
    """
    console.print("\n🤖 [bold blue]Setting Up Your Job Application Profile[/bold blue]")
    
    try:
        from app.services.job_application_service import job_application_service
        
        profile = job_application_service.create_profile_interactive()
        
        console.print(f"\n✅ [bold green]Profile setup complete![/bold green]")
        console.print("Your profile is ready for automated job applications.")
        
    except Exception as e:
        logger.error(f"Error setting up profile: {e}")
        console.print(f"[bold red]❌ Error setting up profile: {e}[/bold red]")

@app.command()
def smart_apply(
    keywords: Annotated[str, typer.Option(help="Job search keywords (e.g., 'Python Developer')")],
    max_applications: Annotated[int, typer.Option(help="Maximum number of applications to submit")] = 5,
    platforms: Annotated[str, typer.Option(help="Platforms to search (comma-separated: indeed,linkedin,remote.co)")] = "indeed,linkedin,remote.co"
):
    """
    🚀 Smart job discovery and automated application across multiple platforms
    
    This command combines job search, AI analysis, and automated applications:
    - Searches across multiple job platforms
    - Uses AI to rank jobs by relevance
    - Automatically applies to the best matches
    - Provides real-time progress tracking
    """
    console.print(f"\n🚀 [bold blue]Smart Job Discovery & Auto-Apply: {keywords}[/bold blue]")
    console.print(f"Max applications: {max_applications}")
    console.print(f"Platforms: {platforms}")
    
    async def run_smart_apply():
        try:
            from app.services.job_application_service import job_application_service
            
            # Check if profile exists
            if not job_application_service.profile:
                console.print("[bold yellow]⚠️ No profile found. Please run 'setup-profile' first.[/bold yellow]")
                return
            
            # Run smart discovery and apply
            results = await job_application_service.smart_job_discovery_and_apply(
                keywords=keywords,
                max_applications=max_applications
            )
            
            # Display results
            console.print(f"\n📊 [bold green]Smart Apply Results[/bold green]")
            console.print(f"Jobs discovered: {results['jobs_discovered']}")
            console.print(f"Applications submitted: {results['applications_submitted']}")
            console.print(f"Platforms searched: {', '.join(results['platforms_searched'])}")
            
            if results['applications']:
                table = Table(title="Application Results")
                table.add_column("Title", style="cyan")
                table.add_column("Company", style="magenta")
                table.add_column("Platform", style="yellow")
                table.add_column("Status", style="green")
                
                for app in results['applications']:
                    status = "✅ Success" if app['success'] else f"❌ Failed: {app.get('error', 'Unknown')}"
                    table.add_row(
                        app['title'],
                        app['company'],
                        app['platform'],
                        status
                    )
                console.print(table)
            
            if results['errors']:
                console.print(f"\n⚠️ [bold yellow]Errors encountered:[/bold yellow]")
                for error in results['errors']:
                    console.print(f"  • {error}")
                    
        except Exception as e:
            logger.error(f"Error in smart apply: {e}")
            console.print(f"[bold red]❌ Error: {e}[/bold red]")
    
    # Run the async function
    asyncio.run(run_smart_apply())

@app.command()
def research_company(
    company_name: Annotated[str, typer.Option(help="Company name to research")],
    keywords: Annotated[str, typer.Option(help="Job keywords to search for at this company")] = "",
    apply_automatically: Annotated[bool, typer.Option("--auto-apply", help="Automatically apply to found jobs")] = False
):
    """
    🔍 Research a company and discover their career opportunities
    
    This command uses AI-powered web browsing to:
    - Find the company's career pages
    - Discover available job opportunities
    - Optionally apply to matching positions
    """
    console.print(f"\n🔍 [bold blue]Researching Company: {company_name}[/bold blue]")
    if keywords:
        console.print(f"Looking for: {keywords}")
    
    async def run_company_research():
        try:
            from app.services.web_browser_service import web_browser_service
            from app.services.job_application_service import job_application_service
            
            # Search for career pages
            console.print("🌐 Searching for company career pages...")
            career_urls = await web_browser_service.search_company_careers(company_name)
            
            if not career_urls:
                console.print(f"[bold yellow]⚠️ No career pages found for {company_name}[/bold yellow]")
                return
            
            console.print(f"✅ Found {len(career_urls)} career page(s):")
            for i, url in enumerate(career_urls, 1):
                console.print(f"  {i}. {url}")
            
            # Scrape jobs from career pages
            all_jobs = []
            for career_url in career_urls[:3]:  # Limit to first 3 pages
                console.print(f"\n📊 Scraping jobs from: {career_url}")
                jobs = await web_browser_service.scrape_career_portal(career_url, keywords)
                all_jobs.extend(jobs)
            
            if not all_jobs:
                console.print(f"[bold yellow]⚠️ No jobs found on {company_name}'s career pages[/bold yellow]")
                return
            
            # Display found jobs
            table = Table(title=f"Jobs at {company_name}")
            table.add_column("Title", style="cyan")
            table.add_column("Location", style="yellow")
            table.add_column("URL", style="blue")
            
            for job in all_jobs:
                table.add_row(
                    job.title,
                    job.location_text,
                    job.job_url[:50] + "..." if len(job.job_url) > 50 else job.job_url
                )
            
            console.print(table)
            
            # Auto-apply if requested
            if apply_automatically and job_application_service.profile:
                console.print(f"\n🚀 Auto-applying to {len(all_jobs)} jobs...")
                
                applied_count = 0
                for job in all_jobs:
                    try:
                        result = await job_application_service.apply_to_job(job)
                        if result.success:
                            applied_count += 1
                            console.print(f"✅ Applied to {job.title}")
                        else:
                            console.print(f"❌ Failed to apply to {job.title}: {result.error_message}")
                    except Exception as e:
                        console.print(f"❌ Error applying to {job.title}: {e}")
                
                console.print(f"\n📊 Applied to {applied_count}/{len(all_jobs)} jobs")
            
            elif apply_automatically:
                console.print("[bold yellow]⚠️ Auto-apply requested but no profile found. Run 'setup-profile' first.[/bold yellow]")
                
        except Exception as e:
            logger.error(f"Error in company research: {e}")
            console.print(f"[bold red]❌ Error: {e}[/bold red]")
    
    # Run the async function
    asyncio.run(run_company_research())

@app.command()
def apply_to_jobs(
    job_ids: Annotated[str, typer.Option(help="Comma-separated job IDs to apply to (from database)")],
    max_applications: Annotated[int, typer.Option(help="Maximum number of applications to submit")] = 10
):
    """
    🎯 Apply to specific jobs by their database IDs
    
    Use this command to apply to jobs you've already discovered and saved.
    Supports bulk application with progress tracking.
    """
    console.print(f"\n🎯 [bold blue]Applying to Jobs[/bold blue]")
    
    try:
        # Parse job IDs
        job_id_list = [int(id.strip()) for id in job_ids.split(',')]
        console.print(f"Job IDs to apply to: {job_id_list}")
        console.print(f"Maximum applications: {max_applications}")
        
        async def run_applications():
            try:
                from app.services.job_application_service import job_application_service
                
                # Check if profile exists
                if not job_application_service.profile:
                    console.print("[bold yellow]⚠️ No profile found. Please run 'setup-profile' first.[/bold yellow]")
                    return
                
                # Apply to jobs
                results = await job_application_service.bulk_apply_to_jobs(
                    job_ids=job_id_list,
                    max_applications=max_applications
                )
                
                # Display results
                successful = sum(1 for r in results if r.success)
                
                console.print(f"\n📊 [bold green]Application Results[/bold green]")
                console.print(f"Total attempted: {len(results)}")
                console.print(f"Successful: {successful}")
                console.print(f"Failed: {len(results) - successful}")
                
                if results:
                    table = Table(title="Application Results")
                    table.add_column("Job Title", style="cyan")
                    table.add_column("Company", style="magenta")
                    table.add_column("Platform", style="yellow")
                    table.add_column("Status", style="green")
                    
                    for result in results:
                        status = "✅ Success" if result.success else f"❌ Failed"
                        table.add_row(
                            result.job_title,
                            result.company_name,
                            result.platform,
                            status
                        )
                    console.print(table)
                    
            except Exception as e:
                logger.error(f"Error in bulk apply: {e}")
                console.print(f"[bold red]❌ Error: {e}[/bold red]")
        
        # Run the async function
        asyncio.run(run_applications())
        
    except ValueError as e:
        console.print(f"[bold red]❌ Invalid job IDs format. Use comma-separated numbers (e.g., '1,2,3')[/bold red]")
    except Exception as e:
        logger.error(f"Error parsing job IDs: {e}")
        console.print(f"[bold red]❌ Error: {e}[/bold red]")

@app.command()
def application_status():
    """
    📊 View your job application history and statistics
    
    Shows a comprehensive overview of all your job applications including:
    - Success rates by platform
    - Recent applications
    - Application trends
    """
    console.print("\n📊 [bold blue]Job Application Status & History[/bold blue]")
    
    try:
        from app.services.job_application_service import job_application_service
        
        summary = job_application_service.get_application_summary()
        
        # Overall statistics
        console.print(f"\n📈 [bold green]Overall Statistics[/bold green]")
        console.print(f"Total applications: {summary['total_applications']}")
        console.print(f"Successful applications: {summary['successful_applications']}")
        console.print(f"Success rate: {summary['success_rate']:.1f}%")
        
        # Platform breakdown
        if summary['platforms']:
            console.print(f"\n🌐 [bold blue]Platform Breakdown[/bold blue]")
            platform_table = Table()
            platform_table.add_column("Platform", style="cyan")
            platform_table.add_column("Total", style="yellow")
            platform_table.add_column("Successful", style="green")
            platform_table.add_column("Success Rate", style="magenta")
            
            for platform, stats in summary['platforms'].items():
                success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
                platform_table.add_row(
                    platform,
                    str(stats['total']),
                    str(stats['successful']),
                    f"{success_rate:.1f}%"
                )
            console.print(platform_table)
        
        # Recent applications
        if summary['recent_applications']:
            console.print(f"\n📅 [bold blue]Recent Applications[/bold blue]")
            recent_table = Table()
            recent_table.add_column("Date", style="dim")
            recent_table.add_column("Title", style="cyan")
            recent_table.add_column("Company", style="magenta")
            recent_table.add_column("Platform", style="yellow")
            recent_table.add_column("Status", style="green")
            
            for app in summary['recent_applications']:
                status = "✅ Success" if app['success'] else "❌ Failed"
                recent_table.add_row(
                    app['date'],
                    app['title'],
                    app['company'],
                    app['platform'],
                    status
                )
            console.print(recent_table)
        
        if summary['total_applications'] == 0:
            console.print("[bold yellow]📭 No applications found. Use 'smart-apply' or 'apply-to-jobs' to start applying![/bold yellow]")
            
    except Exception as e:
        logger.error(f"Error getting application status: {e}")
        console.print(f"[bold red]❌ Error: {e}[/bold red]")

@app.command()
def launch_browser():
    """
    🌐 Launch the Suna-inspired browser interface for real-time job search visualization
    
    This command starts a web server that provides:
    - Real-time browser automation viewing
    - Live task progress tracking  
    - Visual feedback during job scraping
    - Screenshots and browser state monitoring
    
    The interface will be available at http://localhost:8080
    """
    console.print("\n🚀 [bold blue]Launching Suna-Inspired Browser Interface[/bold blue]")
    
    try:
        # Check if required dependencies are installed
        try:
            import fastapi
            import uvicorn
            import websockets
        except ImportError as e:
            console.print(f"❌ [bold red]Missing dependency:[/bold red] {e}")
            console.print("📦 Installing required packages...")
            
            import subprocess
            import sys
            
            packages = ["fastapi", "uvicorn", "websockets"]
            for package in packages:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    console.print(f"✅ Installed {package}")
                except subprocess.CalledProcessError:
                    console.print(f"❌ Failed to install {package}")
                    return
        
        console.print("🔧 Starting browser automation service...")
        
        # Import and start the browser service
        from app.services.browser_automation_service import browser_service
        
        async def start_browser_interface():
            try:
                # Start the browser service
                await browser_service.start_browser()
                console.print("✅ Browser service started")
                
                # Start the web interface
                console.print("🌐 Starting web interface...")
                console.print("📱 Browser interface will be available at:")
                console.print("   http://localhost:8080")
                console.print("   http://127.0.0.1:8080")
                console.print("\n🎮 Features available:")
                console.print("  • Real-time browser viewing")
                console.print("  • Live task progress tracking")
                console.print("  • Screenshot capture")
                console.print("  • Browser state monitoring")
                console.print("\n🔧 To test the interface:")
                console.print("  1. Open http://localhost:8080 in your browser")
                console.print("  2. Run job search commands in another terminal")
                console.print("  3. Watch real-time automation in the web interface")
                console.print("\n⚠️ Press Ctrl+C to stop the browser interface")
                
                # Start the FastAPI server
                import uvicorn
                uvicorn.run(
                    "app.services.browser_automation_service:app",
                    host="127.0.0.1",
                    port=8080,
                    log_level="info"
                )
                
            except Exception as e:
                logger.error(f"Error starting browser interface: {e}")
                console.print(f"❌ [bold red]Error starting browser interface:[/bold red] {e}")
        
        # Run the async function
        asyncio.run(start_browser_interface())
        
    except KeyboardInterrupt:
        console.print("\n🛑 Browser interface stopped by user")
    except Exception as e:
        logger.error(f"Error launching browser interface: {e}")
        console.print(f"❌ [bold red]Error:[/bold red] {e}")
        console.print("\n💡 Troubleshooting:")
        console.print("  • Make sure port 8080 is not in use")
        console.print("  • Check if all dependencies are installed")
        console.print("  • Try running 'pip install fastapi uvicorn websockets'")

@app.command()
def auto_apply():
    """🎯 MAIN GOAL: Automatically apply for LinkedIn jobs"""
    console.print("🎯 LinkedIn Auto-Apply - Your Main Goal!")
    console.print("="*50)
    console.print("🚀 This will automatically find and apply for jobs")
    console.print("✅ Uses your existing LinkedIn automation foundation")
    console.print("⚠️  REAL applications will be submitted!")
    console.print("="*50)
    
    import subprocess
    import sys
    
    try:
        # Run the auto-apply script
        subprocess.run([sys.executable, "linkedin_auto_apply.py"], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Auto-apply failed: {e}")
    except FileNotFoundError:
        console.print("❌ Auto-apply script not found. Make sure linkedin_auto_apply.py exists.")

@app.command()
def auto_apply_fixed():
    """🎯 MAIN GOAL: Automatically apply for LinkedIn jobs (FIXED VERSION)
    
    Uses the proven working job extraction method from linkedin_final_demo.py
    to successfully find and apply to Easy Apply jobs on LinkedIn.
    """
    console.print("🎯 LinkedIn Auto-Apply - FIXED VERSION")
    console.print("="*50)
    console.print("🔧 Using PROVEN job extraction method")
    console.print("🚀 This will automatically find and apply for jobs")
    console.print("✅ Based on successful linkedin_final_demo.py extraction")
    console.print("⚠️  REAL applications will be submitted!")
    console.print("="*50)
    
    import subprocess
    import sys
    
    try:
        # Run the fixed auto-apply script
        subprocess.run([sys.executable, "linkedin_auto_apply_fixed.py"], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Auto-apply failed: {e}")
    except FileNotFoundError:
        console.print("❌ Auto-apply script not found. Make sure linkedin_auto_apply_fixed.py exists.")

@app.command()
def vision_enhanced_apply():
    """🔍 BREAKTHROUGH: Vision-Enhanced LinkedIn Auto-Apply
    
    Uses AI computer vision (Ollama + LLaVA) combined with proven automation
    for the most robust LinkedIn job application system possible.
    
    Features:
    • Standard DOM selectors as primary method
    • AI vision fallback for complex elements
    • Enhanced modal and form detection
    • Visual CAPTCHA solving capability
    • Dynamic UI adaptation
    """
    console.print("🔍 LinkedIn Vision-Enhanced Auto-Apply")
    console.print("="*60)
    console.print("🤖 AI Computer Vision + Proven LinkedIn Automation")
    console.print("🚀 Most robust automation system available")
    console.print("✅ Handles dynamic UIs and complex forms")
    console.print("="*60)
    
    import subprocess
    import sys
    
    try:
        # Run the vision-enhanced auto-apply script
        subprocess.run([sys.executable, "linkedin_vision_enhanced.py"], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Vision-enhanced auto-apply failed: {e}")
        console.print("💡 Make sure:")
        console.print("   1. Ollama is installed and running")
        console.print("   2. LLaVA model is available: ollama pull llava:latest")
        console.print("   3. Vision service dependencies are installed")
    except FileNotFoundError:
        console.print("❌ Vision-enhanced script not found. Make sure linkedin_vision_enhanced.py exists.")

if __name__ == "__main__":
    app() 