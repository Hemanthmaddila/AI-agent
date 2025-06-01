# Application Log Models - Data structures for tracking applications 
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime

class ApplicationLog(BaseModel):
    # Link to job_posting (e.g., by job_url or a foreign key if using an ORM later)
    job_url: HttpUrl = Field(..., example="https://www.linkedin.com/jobs/view/1234567890/")
    job_title: str = Field(..., example="Software Engineer") # Denormalized for easier display/query
    company_name: str = Field(..., example="Tech Innovations Inc.") # Denormalized
    
    application_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(..., example="Applied") # e.g., 'Discovered', 'Preparing', 'Applied', 'Interviewing', 'Offer', 'Rejected', 'Withdrawn'
    
    resume_version_used_path: Optional[str] = Field(None, example="data/output_resumes/resume_for_tech_innovations.pdf")
    cover_letter_version_used_path: Optional[str] = Field(None, example="data/output_resumes/cover_letter_for_tech_innovations.pdf")
    
    notes: Optional[str] = Field(None, example="Followed up on 2025-06-15. Spoke with HR.")
    
    # Timestamps for tracking
    status_last_updated: datetime = Field(default_factory=datetime.utcnow)
    # This 'internal_db_id' would be the primary key from the 'applied_jobs' table after insertion
    internal_db_id: Optional[int] = Field(None, description="Internal database ID for this application log record")

    class Config:
        json_schema_extra = {
            "example": {
                "internal_db_id": 1,
                "job_url": "https://jobs.example.com/listing/123",
                "job_title": "Senior Developer",
                "company_name": "CodeCrafters Ltd.",
                "application_date": "2025-06-01T10:00:00Z",
                "status": "Applied",
                "resume_version_used_path": "data/output_resumes/coder_resume_v3_for_codecrafters.pdf",
                "notes": "Applied via company portal. Referral from John Doe.",
                "status_last_updated": "2025-06-01T10:00:00Z"
            }
        }

if __name__ == '__main__':
    example_log_data = {
        "job_url": "http://jobs.example.com/viewjob/101",
        "job_title": "AI Specialist",
        "company_name": "Future AI Systems",
        "status": "Preparing",
        "notes": "Drafting resume and cover letter."
    }
    app_log = ApplicationLog(**example_log_data)
    print("Successfully created ApplicationLog instance:")
    print(app_log.model_dump_json(indent=2)) 