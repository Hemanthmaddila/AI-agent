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
from app.services.database_service import save_job_posting, save_search_query, get_pending_jobs, update_job_processing_status, save_application_log, find_job_by_url, get_application_logs, get_all_jobs
# Import the GeminiService
from app.services.gemini_service import GeminiService
# We will also need our JobPosting model for type hinting and potentially for displaying
from app.models.job_posting_models import JobPosting
from app.models.application_log_models import ApplicationLog
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
            table.add_column("Field", style="cyan", width=20)
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
    """
    🗑️ Clear LinkedIn session file completely.
    Next LinkedIn scraping will require fresh manual login.
    """
    import os
    from rich.panel import Panel
    
    console.print(f"\n[bold blue]🗑️ Clearing LinkedIn Session[/bold blue]")
    
    session_file = "linkedin_session.json"
    session_path = os.path.join(os.getcwd(), session_file)
    
    try:
        if os.path.exists(session_path):
            # Confirm deletion
            confirm = typer.confirm("Are you sure you want to clear the LinkedIn session? You'll need to login manually next time.")
            
            if confirm:
                os.remove(session_path)
                
                panel = Panel(
                    "🗑️ **Session Cleared Successfully**\n\n"
                    "LinkedIn session file has been permanently deleted.\n"
                    "Next LinkedIn scraping will require fresh manual login.\n\n"
                    "**Privacy Note:** All stored cookies have been removed.",
                    title="Session Clear Complete", 
                    title_align="left",
                    border_style="green"
                )
                console.print(panel)
            else:
                console.print("[yellow]Session clear cancelled.[/yellow]")
        else:
            console.print("[yellow]No LinkedIn session file found to clear.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Error clearing session: {e}[/red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    # Basic logging setup has been moved to the top of the script
    # so it's configured when the module is imported.
    app() 