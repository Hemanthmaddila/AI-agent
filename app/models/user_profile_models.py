# User Profile Models - Data structures for user information 
from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import List, Optional, Dict
from datetime import datetime

class Skill(BaseModel):
    name: str
    proficiency: Optional[str] = None # e.g., "Advanced", "Intermediate"
    years_of_experience: Optional[int] = None

class ExperienceItem(BaseModel):
    job_title: str
    company_name: str
    start_date: str # Consider using date objects later if more complex date logic is needed
    end_date: Optional[str] = None # Can be "Present" or a specific date
    description_points: List[str]
    skills_used: Optional[List[str]] = None

class EducationItem(BaseModel):
    institution_name: str
    degree: str
    field_of_study: Optional[str] = None
    graduation_date: Optional[str] = None # Or year
    gpa: Optional[float] = None

class UserProfile(BaseModel):
    profile_name: str = Field(..., example="software_engineer_cloud") # e.g., "software_engineer_cloud"
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None
    
    base_resume_path: Optional[str] = None # Path to the master resume file for this profile
    summary_statement: Optional[str] = None # Professional summary or objective
    
    skills: List[Skill] = []
    experiences: List[ExperienceItem] = []
    education: List[EducationItem] = []
    
    # Preferences for job search
    target_roles: List[str] = []
    target_industries: List[str] = []
    preferred_locations: List[str] = [] # e.g., ["Remote", "Austin, TX"]
    salary_expectations_min: Optional[int] = None
    salary_expectations_max: Optional[int] = None
    job_type_preferences: List[str] = [] # e.g., ["Full-time", "Contract"]
    company_culture_preferences: List[str] = []
    
    # For storing answers to common application questions
    custom_questions_answers: Dict[str, str] = {} 
    # e.g., {"Why are you interested in this type of role?": "My answer...", 
    #        "Describe a challenging project.": "Details about project..."}

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Example usage within the model for documentation or testing
    class Config:
        # schema_extra is deprecated, use model_config with json_schema_extra in Pydantic v2
        # For Pydantic v1.x
        # schema_extra = {
        #     "example": {
        #         "profile_name": "sr_python_developer_remote",
        #         "full_name": "Alex Doe",
        #         "email": "alex.doe@example.com",
        #         "base_resume_path": "data/resumes/alex_doe_base.pdf",
        #         "target_roles": ["Senior Python Developer", "Backend Engineer"],
        #         "preferred_locations": ["Remote"],
        #     }
        # }
        # For Pydantic v2.x
        json_schema_extra = {
            "example": {
                "profile_name": "sr_python_developer_remote",
                "full_name": "Alex Doe",
                "email": "alex.doe@example.com",
                "base_resume_path": "data/resumes/alex_doe_base.pdf", # This path would be relative to project root or a defined data dir
                "target_roles": ["Senior Python Developer", "Backend Engineer"],
                "preferred_locations": ["Remote"],
                "skills": [{"name": "Python", "proficiency": "Advanced", "years_of_experience": 5}],
                "created_at": "2024-05-31T12:00:00Z",
                "last_updated_at": "2024-05-31T12:00:00Z"
            }
        }

if __name__ == '__main__':
    # Example of creating a UserProfile instance
    example_profile_data = {
        "profile_name": "software_dev_example",
        "full_name": "Jane Dev",
        "email": "jane.dev@example.com",
        "phone": "123-456-7890",
        "linkedin_url": "http://linkedin.com/in/janedev",
        "base_resume_path": "resumes/jane_dev_main.pdf",
        "summary_statement": "Experienced software developer...",
        "skills": [
            {"name": "Python", "proficiency": "Expert", "years_of_experience": 5},
            {"name": "FastAPI", "proficiency": "Intermediate", "years_of_experience": 2}
        ],
        "experiences": [
            {
                "job_title": "Senior Developer", "company_name": "Tech Solutions Inc.",
                "start_date": "2022-01-01", "end_date": "Present",
                "description_points": ["Led a team of 5 developers.", "Developed and maintained critical APIs."]
            }
        ],
        "education": [
            {"institution_name": "State University", "degree": "B.S. in Computer Science", "graduation_date": "2021-05-01"}
        ],
        "target_roles": ["Software Engineer", "Backend Developer"],
        "preferred_locations": ["Remote", "New York, NY"],
        "custom_questions_answers": {
            "What are your strengths?": "Problem-solving, quick learning, and teamwork."
        }
    }
    
    user_profile = UserProfile(**example_profile_data)
    print("Successfully created UserProfile instance:")
    # Using model_dump_json for Pydantic v2. For v1, it would be user_profile.json(indent=2)
    print(user_profile.model_dump_json(indent=2)) 