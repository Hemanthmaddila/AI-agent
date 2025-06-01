# SerpAPI Client - Job search API integration 
from serpapi import GoogleSearch # SerpAPI client library
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

# Conditional import for config - handled differently when run directly vs imported
try:
    from config import settings # To access SERPAPI_API_KEY
    from app.models.job_posting_models import JobPosting # Our Pydantic model
except ImportError:
    # When running directly, we'll handle this in the main block
    settings = None
    JobPosting = None

# It's good practice to use a logger for services
logger = logging.getLogger(__name__) # Will inherit root logger settings from main.py if configured there

class SerpApiClient:
    def __init__(self, api_key: Optional[str] = None):
        # Handle API key from parameter or settings
        if api_key is None and settings is not None:
            api_key = settings.SERPAPI_API_KEY
            
        if not api_key:
            logger.error("SerpAPI key not provided or configured in .env file.")
            # Depending on how critical this is, you might raise an error
            # or allow it to be instantiated and fail on method call.
            # For a service client, failing early is often good.
            raise ValueError("SerpAPI key is required for SerpApiClient.")
        self.api_key = api_key

    def search_google_jobs(self, query: str, location: Optional[str] = None, num_results: int = 10) -> List:
        """
        Searches Google Jobs using SerpAPI.

        Args:
            query: The job search query (e.g., "Python Developer").
            location: The location for the job search (e.g., "Remote", "Austin, TX").
            num_results: The number of job results to fetch.

        Returns:
            A list of JobPosting Pydantic objects.
        """
        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": self.api_key,
            "num": str(num_results) # API expects num as string for some endpoints
        }
        if location:
            params["location"] = location

        logger.info(f"Searching Google Jobs via SerpAPI. Query: '{query}', Location: '{location}', Num: {num_results}")

        try:
            search = GoogleSearch(params)
            results_dict = search.get_dict() # Get results as a Python dictionary

            if "error" in results_dict:
                logger.error(f"SerpAPI returned an error: {results_dict['error']}")
                return []
            
            if "jobs_results" not in results_dict or not results_dict["jobs_results"]:
                logger.info("No job results found from SerpAPI for the given query.")
                return []

            job_postings: List = []
            for job_data in results_dict["jobs_results"]:
                # Mapping SerpAPI fields to our JobPosting model
                # This mapping needs to be robust and handle missing fields gracefully
                job_url = "https://jobs.google.com"  # Default fallback URL
                if job_data.get("related_links") and job_data["related_links"][0].get("link"):
                    job_url = job_data["related_links"][0]["link"]
                elif job_data.get("job_highlight", {}).get("apply_options"):
                    # Sometimes apply options contain direct links
                    apply_options = job_data["job_highlight"]["apply_options"]
                    if apply_options and apply_options[0].get("link"):
                        job_url = apply_options[0]["link"]
                
                # Ensure we have a valid URL for HttpUrl validation
                if not job_url.startswith(('http://', 'https://')):
                    job_url = f"https://{job_url}"
                
                description_snippet = job_data.get("description", "")
                # In MVP, 'full_description_raw' might be just the snippet.
                # For full descriptions, we'd typically need to visit job_url (Phase 4).

                # Date posted parsing can be tricky. SerpAPI provides 'detected_extensions.posted_at'
                # For MVP, we'll store the text. Parsing to ISO datetime can be added.
                date_posted_text = job_data.get("detected_extensions", {}).get("posted_at")

                # Extract salary information if available
                salary_range_text = None
                salary_min = None
                salary_max = None
                if job_data.get("detected_extensions", {}).get("salary"):
                    salary_range_text = job_data["detected_extensions"]["salary"]

                # Create JobPosting object if available, otherwise a dict for testing
                if JobPosting is not None:
                    job_posting = JobPosting(
                        source_platform="SerpApi_GoogleJobs",
                        job_url=job_url, # Ensure this is a valid HttpUrl or handle conversion
                        title=job_data.get("title", "N/A"),
                        company_name=job_data.get("company_name", "N/A"),
                        location_text=job_data.get("location"),
                        date_posted_text=date_posted_text,
                        full_description_raw=description_snippet, # For MVP, this is the description snippet
                        full_description_text=description_snippet, # Cleaned text version
                        salary_range_text=salary_range_text,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        id_on_platform=job_data.get("job_id"), # SerpAPI's job_id for this posting
                        scraped_timestamp=datetime.utcnow(), # Set current time
                        processing_status="Pending" # Initial status
                        # Other fields like relevance_score will be populated later by AI analysis
                    )
                else:
                    # Fallback dict for direct testing
                    job_posting = {
                        "source_platform": "SerpApi_GoogleJobs",
                        "job_url": job_url,
                        "title": job_data.get("title", "N/A"),
                        "company_name": job_data.get("company_name", "N/A"),
                        "location_text": job_data.get("location"),
                        "date_posted_text": date_posted_text,
                        "full_description_text": description_snippet,
                        "id_on_platform": job_data.get("job_id"),
                        "scraped_timestamp": datetime.utcnow().isoformat()
                    }
                
                job_postings.append(job_posting)
            
            logger.info(f"Successfully fetched and mapped {len(job_postings)} jobs from SerpAPI.")
            return job_postings

        except Exception as e:
            logger.error(f"An exception occurred during SerpAPI call or data mapping: {e}", exc_info=True)
            return []

# Example usage for testing this client directly (optional)
if __name__ == "__main__":
    import sys
    import os
    # Add the project root to Python path for direct testing
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, project_root)
    
    # Now import after path adjustment
    from config import settings
    from app.models.job_posting_models import JobPosting
    
    # Basic logging setup for testing this script
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ensure you have SERPAPI_API_KEY in your .env file for this direct test
    if not settings.SERPAPI_API_KEY:
        print("SERPAPI_API_KEY not found in .env file. Please add it to test serpapi_client.py directly.")
        print("Add this line to your .env file: SERPAPI_API_KEY=your_api_key_here")
    else:
        try:
            client = SerpApiClient(api_key=settings.SERPAPI_API_KEY)
            # Test search
            print("\nTesting SerpAPI client with query: 'Software Engineer', location: 'Remote'")
            jobs = client.search_google_jobs(query="Software Engineer", location="Remote", num_results=3)
            
            if jobs:
                print(f"\nFound {len(jobs)} jobs:")
                for i, job in enumerate(jobs):
                    if hasattr(job, 'title'):  # Pydantic object
                        print(f"  {i+1}. {job.title} at {job.company_name}")
                        print(f"     URL: {job.job_url}")
                        print(f"     Location: {job.location_text}")
                        if job.full_description_text:
                            print(f"     Description Snippet: {job.full_description_text[:100]}...")
                    else:  # Dict object
                        print(f"  {i+1}. {job['title']} at {job['company_name']}")
                        print(f"     URL: {job['job_url']}")
                        print(f"     Location: {job['location_text']}")
                        if job['full_description_text']:
                            print(f"     Description Snippet: {job['full_description_text'][:100]}...")
                    print()
                    # print(job.model_dump_json(indent=2)) # For full model details
            else:
                print("No jobs found or an error occurred.")
        except ValueError as ve:
            print(f"Error initializing client: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}") 