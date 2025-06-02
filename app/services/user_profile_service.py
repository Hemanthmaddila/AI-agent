"""
User Profile Service - Manages user profiles for job applications
"""
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.models.user_profile_models import UserProfile

logger = logging.getLogger(__name__)

class UserProfileService:
    """Service for managing user profiles"""
    
    def __init__(self):
        self.profiles_dir = Path("data/user_profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
    def load_profile(self, profile_name: str) -> Optional[UserProfile]:
        """Load a user profile by name"""
        try:
            profile_file = self.profiles_dir / f"{profile_name}.json"
            if not profile_file.exists():
                logger.warning(f"Profile file not found: {profile_file}")
                return None
                
            with open(profile_file, 'r') as f:
                profile_data = json.load(f)
                
            return UserProfile(**profile_data)
            
        except Exception as e:
            logger.error(f"Error loading profile {profile_name}: {e}")
            return None
    
    def save_profile(self, profile: UserProfile) -> bool:
        """Save a user profile"""
        try:
            profile_file = self.profiles_dir / f"{profile.profile_name}.json"
            
            with open(profile_file, 'w') as f:
                json.dump(profile.model_dump(), f, indent=2, default=str)
                
            logger.info(f"Profile saved: {profile_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving profile {profile.profile_name}: {e}")
            return False
    
    def list_profiles(self) -> List[str]:
        """List all available profile names"""
        try:
            profile_files = list(self.profiles_dir.glob("*.json"))
            return [f.stem for f in profile_files]
            
        except Exception as e:
            logger.error(f"Error listing profiles: {e}")
            return []
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a user profile"""
        try:
            profile_file = self.profiles_dir / f"{profile_name}.json"
            if profile_file.exists():
                profile_file.unlink()
                logger.info(f"Profile deleted: {profile_name}")
                return True
            else:
                logger.warning(f"Profile not found: {profile_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting profile {profile_name}: {e}")
            return False
    
    def create_default_profile(self) -> UserProfile:
        """Create a default profile for testing"""
        default_profile = UserProfile(
            profile_name="default",
            full_name="Demo User",
            email="demo@example.com",
            phone="(555) 123-4567",
            linkedin_url="https://linkedin.com/in/demo-user",
            github_url="https://github.com/demo-user",
            summary_statement="Experienced software developer with expertise in Python and web development.",
            target_roles=["Software Engineer", "Backend Developer", "Full Stack Developer"],
            preferred_locations=["Remote", "San Francisco, CA", "New York, NY"],
            custom_questions_answers={
                "Why are you interested in this role?": "I'm passionate about building scalable software solutions and contributing to innovative projects.",
                "What are your strengths?": "Strong problem-solving skills, attention to detail, and ability to work well in collaborative environments.",
                "Tell us about a challenging project": "I recently led the development of a microservices architecture that improved system performance by 40%."
            }
        )
        
        # Save the default profile
        self.save_profile(default_profile)
        return default_profile 