# Main CLI Entry Point - Command line interface for the AI agent 
import typer
from rich.console import Console
from rich.table import Table # Import Table for displaying results
import os # For path operations
import sys # For stdout logging handler
import logging # Import logging
from typing import List # For type hinting
from typing_extensions import Annotated # For newer Typer versions

# Assuming your settings and future orchestrator/services will be in the 'app' package
# and config.settings loads everything we need.
from config import settings # This will load .env and make settings available
# Import the newly created SerpApiClient
from app.services.serpapi_client import SerpApiClient
# We will also need our JobPosting model for type hinting and potentially for displaying
from app.models.job_posting_models import JobPosting

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
    location: Annotated[str, typer.Option(help="Location for the job search (e.g., 'Remote', 'Austin, TX').")] = None,
    num_results: Annotated[int, typer.Option(help="Number of results to fetch.")] = 10
):
    """
    Finds job postings from SerpAPI (Google Jobs) based on keywords and location.
    """
    console.print(f"\n[bold blue]🔎 Finding jobs with keywords '{keywords}'[/bold blue]")
    if location:
        console.print(f"Location: '{location}'")
    console.print(f"Number of results to fetch: {num_results}")
    logger.info(f"find_jobs command initiated with keywords: '{keywords}', location: '{location}', num_results: {num_results}")

    if not settings.SERPAPI_API_KEY:
        logger.error("SERPAPI_API_KEY is not configured in .env.")
        console.print("[bold red]ERROR: SERPAPI_API_KEY is not configured in .env.[/bold red]")
        console.print("Please add SERPAPI_API_KEY to your .env file to use the find-jobs command.")
        raise typer.Exit(code=1)
        
    try:
        client = SerpApiClient() # API key is handled by the client's __init__
        console.print("Attempting to fetch jobs via SerpAPI...")
        jobs_found: List[JobPosting] = client.search_google_jobs(
            query=keywords, 
            location=location, 
            num_results=num_results
        )

        if jobs_found:
            console.print(f"\n[bold green]✅ Found {len(jobs_found)} jobs:[/bold green]")
            
            table = Table(title="Discovered Jobs (Raw from SerpAPI)")
            table.add_column("No.", style="dim", width=4)
            table.add_column("Title", style="cyan", min_width=30)
            table.add_column("Company", style="magenta", min_width=20)
            table.add_column("Location", style="yellow", min_width=15)
            table.add_column("URL", style="blue", overflow="fold") # Fold long URLs

            for i, job in enumerate(jobs_found):
                table.add_row(
                    str(i + 1),
                    job.title if job.title else "N/A",
                    job.company_name if job.company_name else "N/A",
                    job.location_text if job.location_text else "N/A",
                    str(job.job_url) if job.job_url else "N/A"
                )
            console.print(table)
            logger.info(f"Displayed {len(jobs_found)} jobs to the user.")
            # TODO MVP Next Step: Save these jobs_found to the database.
            console.print("\nNext step would be to save these jobs to the database and allow further processing.")
        else:
            console.print("[yellow]No jobs found for the given criteria from SerpAPI.[/yellow]")
            logger.info("No jobs found from SerpAPI for the given criteria.")

    except ValueError as ve: # Catch API key error from SerpApiClient instantiation
        logger.error(f"ValueError during SerpAPI client usage: {ve}")
        console.print(f"[bold red]Client Error: {ve}[/bold red]")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during find_jobs: {e}", exc_info=True)
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        raise typer.Exit(code=1)

# Add other commands here as we build them, for example:
# @app.command()
# def process_jobs():
#     """Processes raw job postings for relevance."""
#     console.print("Processing jobs...")

# @app.command()
# def tailor_resume(job_id: int, resume_path: str):
#    """Tailors a resume for a specific job."""
#    console.print(f"Tailoring resume {resume_path} for job ID {job_id}...")

@app.command()
def log_application(
    job_url: Annotated[str, typer.Option(help="The URL of the job you applied for.")],
    resume_path: Annotated[str, typer.Option(help="Path to the resume version used for this application.")], 
    status: Annotated[str, typer.Option(help="Status of the application (e.g., 'Applied', 'Submitted').")] = "Applied",
    notes: Annotated[str, typer.Option(help="Any notes about this application.")] = None
):
    """
    Manually logs a job application to the database.
    """
    console.print(f"\n[bold blue]📝 Logging application for job URL: {job_url}[/bold blue]")
    console.print(f"Resume used: {resume_path}")
    console.print(f"Status: {status}")
    if notes:
        console.print(f"Notes: {notes}")
    
    # TODO MVP Step (later in workflow):
    # 1. Create ApplicationLog Pydantic model instance.
    # 2. (Optional) Try to fetch job title/company from job_postings_raw if URL exists, else ask or leave blank.
    # 3. Save to 'applied_jobs' table using database_service.
    # 4. Confirm to user.
    console.print("\n[bold yellow]🚧 MVP: `log_application` command structure is set up.[/bold yellow]")
    console.print("Next steps: Implement database saving logic.")
    logger.info(f"log_application command called for job_url: {job_url}")


if __name__ == "__main__":
    # Basic logging setup has been moved to the top of the script
    # so it's configured when the module is imported.
    app() 