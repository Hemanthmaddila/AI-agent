"""
Human-in-the-Loop (HITL) Service

Provides interactive review and confirmation capabilities for the AI Job Application Agent.
Ensures human oversight for critical automation steps like job applications.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

from app.models.user_profile_models import UserProfile
from app.models.job_posting_models import JobPosting

logger = logging.getLogger(__name__)

class HITLService:
    """
    Service for Human-in-the-Loop interactions during automated processes.
    
    Provides methods for:
    - Interactive confirmation prompts
    - Data review and validation
    - Manual input collection
    - Safety checks before automation
    """
    
    def __init__(self):
        self.session_logs = []
        logger.info("HITLService initialized")
    
    def confirm_action(self, 
                      action_description: str, 
                      context: Dict[str, Any] = None,
                      default_response: bool = False) -> bool:
        """
        Get user confirmation for an action.
        
        Args:
            action_description: Description of the action requiring confirmation
            context: Additional context information
            default_response: Default response if user just presses Enter
            
        Returns:
            True if user confirms, False otherwise
        """
        try:
            print(f"\n🤖 CONFIRMATION REQUIRED")
            print("-" * 50)
            print(f"Action: {action_description}")
            
            if context:
                print("\nContext:")
                for key, value in context.items():
                    print(f"  {key}: {value}")
            
            default_text = "Y/n" if default_response else "y/N"
            while True:
                response = input(f"\nProceed? ({default_text}): ").strip().lower()
                
                if not response:
                    return default_response
                elif response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no']:
                    return False
                else:
                    print("Please enter 'y' for yes or 'n' for no")
                    
        except KeyboardInterrupt:
            print("\n❌ Action cancelled by user")
            return False
        except Exception as e:
            logger.error(f"Error in confirm_action: {e}")
            return False
    
    def review_job_application_data(self, 
                                  job: JobPosting, 
                                  user_profile: UserProfile,
                                  filled_fields: Dict[str, bool]) -> bool:
        """
        Review job application data before submission.
        
        Args:
            job: Job posting being applied to
            user_profile: User profile used for application
            filled_fields: Dictionary of successfully filled fields
            
        Returns:
            True if user approves the data, False otherwise
        """
        try:
            print("\n" + "="*80)
            print("📋 JOB APPLICATION REVIEW")
            print("="*80)
            
            # Job information
            print(f"🏢 Company: {job.company_name}")
            print(f"💼 Position: {job.title}")
            print(f"📍 Location: {job.location or 'Not specified'}")
            print(f"🔗 URL: {job.job_url}")
            
            # User profile information
            print(f"\n👤 Profile: {user_profile.profile_name}")
            print(f"📧 Email: {user_profile.email}")
            print(f"📱 Phone: {user_profile.phone or 'Not provided'}")
            
            # Filled fields summary
            print(f"\n✅ Successfully filled fields:")
            for field_type, success in filled_fields.items():
                status = "✅" if success else "❌"
                print(f"  {status} {field_type}")
            
            # Safety checks
            warnings = []
            if not user_profile.email:
                warnings.append("No email address provided")
            if not user_profile.phone:
                warnings.append("No phone number provided")
            if len([f for f in filled_fields.values() if f]) < 3:
                warnings.append("Very few fields were successfully filled")
            
            if warnings:
                print(f"\n⚠️  WARNINGS:")
                for warning in warnings:
                    print(f"  • {warning}")
            
            print("-" * 80)
            
            return self.confirm_action(
                f"Submit application for {job.title} at {job.company_name}",
                context={
                    "Filled fields": f"{len([f for f in filled_fields.values() if f])}/{len(filled_fields)}",
                    "Profile": user_profile.profile_name,
                    "Email": str(user_profile.email) if user_profile.email else "None"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in review_job_application_data: {e}")
            return False
    
    def collect_missing_information(self, 
                                  required_fields: List[str],
                                  current_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Interactively collect missing information from user.
        
        Args:
            required_fields: List of field names that need values
            current_data: Current data values
            
        Returns:
            Dictionary of collected values
        """
        collected_data = {}
        
        try:
            print(f"\n📝 MISSING INFORMATION COLLECTION")
            print("-" * 50)
            print("Some required fields are missing. Please provide the following:")
            
            for field in required_fields:
                current_value = current_data.get(field, "")
                
                if current_value:
                    prompt = f"{field} (current: {current_value}): "
                else:
                    prompt = f"{field}: "
                
                while True:
                    value = input(prompt).strip()
                    
                    if value:
                        collected_data[field] = value
                        break
                    elif current_value:
                        # Use current value if user just presses Enter
                        collected_data[field] = current_value
                        break
                    else:
                        print(f"  ⚠️  {field} is required. Please provide a value.")
            
            return collected_data
            
        except KeyboardInterrupt:
            print("\n❌ Data collection cancelled by user")
            return {}
        except Exception as e:
            logger.error(f"Error in collect_missing_information: {e}")
            return {}
    
    def review_and_edit_profile(self, user_profile: UserProfile) -> Optional[UserProfile]:
        """
        Allow user to review and edit profile data interactively.
        
        Args:
            user_profile: Current user profile
            
        Returns:
            Updated user profile or None if cancelled
        """
        try:
            print(f"\n👤 PROFILE REVIEW: {user_profile.profile_name}")
            print("-" * 50)
            
            # Display current profile data
            profile_fields = {
                'full_name': user_profile.full_name,
                'email': str(user_profile.email) if user_profile.email else "",
                'phone': user_profile.phone or "",
                'linkedin_url': str(user_profile.linkedin_url) if user_profile.linkedin_url else "",
                'github_url': str(user_profile.github_url) if user_profile.github_url else "",
                'summary_statement': user_profile.summary_statement or ""
            }
            
            print("Current profile data:")
            for field, value in profile_fields.items():
                print(f"  {field}: {value or '(not set)'}")
            
            if not self.confirm_action("Edit profile data?", default_response=False):
                return user_profile
            
            # Collect updated data
            updated_data = self.collect_missing_information(
                list(profile_fields.keys()),
                profile_fields
            )
            
            if updated_data:
                # Update profile with new data
                for field, value in updated_data.items():
                    if value:  # Only update non-empty values
                        setattr(user_profile, field, value)
                
                user_profile.last_updated_at = datetime.utcnow()
                
                print("✅ Profile updated successfully")
                return user_profile
            else:
                print("❌ No changes made to profile")
                return user_profile
                
        except Exception as e:
            logger.error(f"Error in review_and_edit_profile: {e}")
            return user_profile
    
    def show_application_summary(self, 
                               job: JobPosting,
                               result: Dict[str, Any]) -> None:
        """
        Display a summary of the application process results.
        
        Args:
            job: Job that was applied to
            result: Application process result dictionary
        """
        try:
            print("\n" + "="*80)
            print("📊 APPLICATION SUMMARY")
            print("="*80)
            
            print(f"🏢 Company: {job.company_name}")
            print(f"💼 Position: {job.title}")
            print(f"🕒 Timestamp: {result.get('timestamp', 'Unknown')}")
            print(f"✅ Success: {'Yes' if result.get('success', False) else 'No'}")
            
            # Show filled fields
            filled_fields = result.get('filled_fields', {})
            if filled_fields:
                successful_fields = [f for f, success in filled_fields.items() if success]
                failed_fields = [f for f, success in filled_fields.items() if not success]
                
                print(f"\n📝 Form Fields:")
                print(f"  ✅ Successfully filled: {len(successful_fields)}")
                if successful_fields:
                    for field in successful_fields:
                        print(f"    • {field}")
                
                if failed_fields:
                    print(f"  ❌ Failed to fill: {len(failed_fields)}")
                    for field in failed_fields:
                        print(f"    • {field}")
            
            # Show errors
            errors = result.get('errors', [])
            if errors:
                print(f"\n⚠️  Errors encountered:")
                for error in errors:
                    print(f"  • {error}")
            
            # Show screenshot path
            screenshot_path = result.get('screenshot_path', '')
            if screenshot_path and os.path.exists(screenshot_path):
                print(f"\n📸 Screenshot saved: {screenshot_path}")
            
            print("-" * 80)
            
        except Exception as e:
            logger.error(f"Error in show_application_summary: {e}")
    
    def log_session_event(self, event_type: str, description: str, data: Dict[str, Any] = None):
        """
        Log an event from the current HITL session.
        
        Args:
            event_type: Type of event (e.g., 'confirmation', 'review', 'edit')
            description: Human-readable description of the event
            data: Additional event data
        """
        event = {
            'timestamp': datetime.utcnow(),
            'type': event_type,
            'description': description,
            'data': data or {}
        }
        
        self.session_logs.append(event)
        logger.info(f"HITL Event: {event_type} - {description}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current HITL session.
        
        Returns:
            Dictionary containing session statistics and events
        """
        return {
            'total_events': len(self.session_logs),
            'session_start': self.session_logs[0]['timestamp'] if self.session_logs else None,
            'session_end': self.session_logs[-1]['timestamp'] if self.session_logs else None,
            'events': self.session_logs
        }

# Global instance for easy access
_hitl_service = None

def get_hitl_service() -> HITLService:
    """
    Get or create the global HITL service instance.
    
    Returns:
        HITLService instance
    """
    global _hitl_service
    if _hitl_service is None:
        _hitl_service = HITLService()
    return _hitl_service 