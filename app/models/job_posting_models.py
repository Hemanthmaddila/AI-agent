# Job Posting Models - Data structures for job postings 
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict
from datetime import datetime

class JobPosting(BaseModel):
    id_on_platform: Optional[str] = Field(None, example="linkedin_job_123") # e.g., LinkedIn job ID
    source_platform: str = Field(..., example="LinkedIn") # e.g., "LinkedIn", "Indeed", "SerpApi_GoogleJobs"
    job_url: HttpUrl = Field(..., example="https://www.linkedin.com/jobs/view/1234567890/")
    title: str = Field(..., example="Software Engineer")
    company_name: str = Field(..., example="Tech Innovations Inc.")
    location_text: Optional[str] = Field(None, example="San Francisco, CA or Remote")
    
    date_posted_text: Optional[str] = Field(None, example="Posted 2 days ago") # Raw text like "Posted 2 days ago"
    date_posted_iso: Optional[datetime] = Field(None, example="2024-05-29T10:00:00Z") # Parsed date
    
    full_description_raw: Optional[str] = Field(None, example="<p>Join our team...</p>") # The full HTML or Markdown of the job description
    full_description_text: Optional[str] = Field(None, example="Join our team...") # Cleaned text version
    
    salary_range_text: Optional[str] = Field(None, example="$100,000 - $150,000 per year")
    salary_min: Optional[float] = Field(None, example=100000.00)
    salary_max: Optional[float] = Field(None, example=150000.00)
    currency: Optional[str] = Field(None, example="USD")
    
    skills_extracted: List[str] = Field(default_factory=list, example=["Python", "FastAPI", "SQL"]) # Skills extracted by NLP/AI
    
    relevance_score: Optional[float] = Field(None, example=4.5) # Calculated by AI (e.g., 1-5 scale)
    match_score_details: Optional[Dict[str, float]] = Field(None, example={"skill_alignment": 0.8, "culture_fit": 0.6}) # Breakdown of MatchScore components
    
    is_remote: Optional[bool] = Field(None, example=True)
    
    scraped_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Internal agent fields
    processing_status: str = Field("Pending", example="Pending") # e.g., 'Pending', 'Analyzed_Relevant', 'Analyzed_Irrelevant', 'Error'
    # This 'id' is for the internal database, distinct from 'id_on_platform'
    internal_db_id: Optional[int] = Field(None, description="Internal database ID for this job posting record in job_postings_raw table")


    class Config:
        json_schema_extra = {
            "example": {
                "id_on_platform": "jb12345",
                "source_platform": "SerpApi_GoogleJobs",
                "job_url": "https://jobs.google.com/example/123",
                "title": "Senior Python Developer",
                "company_name": "FutureTech Solutions",
                "location_text": "Remote (USA)",
                "date_posted_text": "3 hours ago",
                "date_posted_iso": "2025-05-31T14:00:00Z",
                "full_description_text": "We are seeking an experienced Python developer to join our innovative team...",
                "salary_min": 120000,
                "salary_max": 160000,
                "currency": "USD",
                "skills_extracted": ["Python", "Django", "AWS", "PostgreSQL"],
                "relevance_score": 4.7,
                "is_remote": True,
                "scraped_timestamp": "2025-05-31T17:30:00Z",
                "processing_status": "Pending"
            }
        }

if __name__ == '__main__':
    # Example of creating a JobPosting instance
    example_job_data = {
        "id_on_platform": "indeed_789",
        "source_platform": "Indeed",
        "job_url": "http://jobs.indeed.com/viewjob/789",
        "title": "Data Scientist",
        "company_name": "Data Insights Co.",
        "location_text": "New York, NY",
        "full_description_text": "Looking for a skilled Data Scientist to analyze large datasets...",
        "skills_extracted": ["Python", "Machine Learning", "R", "Statistics"],
        "is_remote": False,
        "processing_status": "Pending"
    }
    job_posting = JobPosting(**example_job_data)
    print("Successfully created JobPosting instance:")
    print(job_posting.model_dump_json(indent=2)) 