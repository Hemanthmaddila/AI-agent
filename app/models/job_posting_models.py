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
    
    # Salary and compensation
    salary_range_text: Optional[str] = Field(None, example="$100,000 - $150,000 per year")
    salary_min: Optional[float] = Field(None, example=100000.00)
    salary_max: Optional[float] = Field(None, example=150000.00)
    currency: Optional[str] = Field(None, example="USD")
    
    # Startup-specific equity and funding fields (for platforms like Wellfound)
    equity_min_percent: Optional[float] = Field(None, example=0.01, description="Minimum equity offered (e.g., 0.01 for 1%)")
    equity_max_percent: Optional[float] = Field(None, example=0.1, description="Maximum equity offered (e.g., 0.1 for 10%)")
    equity_range_text: Optional[str] = Field(None, example="0.01% - 0.1%", description="Equity range as text if specific min/max not available")
    
    funding_stage: Optional[str] = Field(None, example="Series A", description="Company funding stage (Seed, Series A, B, etc.)")
    company_size_range: Optional[str] = Field(None, example="11-50 employees", description="Range for company size")
    company_total_funding: Optional[float] = Field(None, example=5000000.00, description="Total funding raised by company in USD")
    
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
                "source_platform": "Wellfound",
                "job_url": "https://wellfound.com/l/2A1B3C4D5E",
                "title": "Senior Full-Stack Engineer",
                "company_name": "TechStart Inc",
                "location_text": "San Francisco, CA / Remote",
                "date_posted_text": "3 hours ago",
                "date_posted_iso": "2025-05-31T14:00:00Z",
                "full_description_text": "Join our fast-growing startup building the future of AI-powered analytics...",
                "salary_min": 120000,
                "salary_max": 160000,
                "currency": "USD",
                "equity_min_percent": 0.001,  # 0.1%
                "equity_max_percent": 0.01,   # 1.0%
                "equity_range_text": "0.1% - 1.0%",
                "funding_stage": "Series A",
                "company_size_range": "11-50 employees",
                "company_total_funding": 8500000.00,
                "skills_extracted": ["Python", "React", "TypeScript", "AWS", "PostgreSQL"],
                "relevance_score": 4.7,
                "is_remote": True,
                "scraped_timestamp": "2025-05-31T17:30:00Z",
                "processing_status": "Pending"
            }
        }

if __name__ == '__main__':
    # Example of creating a JobPosting instance with startup data
    example_job_data = {
        "id_on_platform": "wellfound_789",
        "source_platform": "Wellfound",
        "job_url": "http://wellfound.com/l/startup-job-789",
        "title": "Data Scientist",
        "company_name": "AI Startup Co.",
        "location_text": "Remote (US)",
        "full_description_text": "Looking for a skilled Data Scientist to join our Series A startup and analyze large datasets...",
        "equity_min_percent": 0.005,  # 0.5%
        "equity_max_percent": 0.02,   # 2.0%
        "funding_stage": "Series A",
        "company_size_range": "25-50",
        "skills_extracted": ["Python", "Machine Learning", "R", "Statistics"],
        "is_remote": True,
        "processing_status": "Pending"
    }
    job_posting = JobPosting(**example_job_data)
    print("Successfully created JobPosting instance with startup data:")
    print(job_posting.model_dump_json(indent=2)) 