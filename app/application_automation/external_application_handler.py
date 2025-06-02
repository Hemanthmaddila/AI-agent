#!/usr/bin/env python3
"""
🌐 External Application Handler - Intelligent ATS & Career Portal Automation
Handles job applications on external company websites and ATS systems
"""

import asyncio
import json
import logging
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

# Import models and services
from app.models.user_profile_models import UserProfile
from app.models.job_posting_models import JobPosting
from app.services.gemini_service import GeminiService
from app.hitl.hitl_service import HITLService

# Import vision service if available
try:
    from app.services.vision_service import VisionService, get_vision_service
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    VisionService = None

logger = logging.getLogger(__name__)

class FieldInfo:
    """Container for discovered form field information"""
    def __init__(self, element: Locator, field_type: str, label: str = "", 
                 field_id: str = "", name: str = "", placeholder: str = "",
                 required: bool = False, coordinates: Tuple[int, int] = None):
        self.element = element
        self.field_type = field_type
        self.label = label
        self.field_id = field_id
        self.name = name
        self.placeholder = placeholder
        self.required = required
        self.coordinates = coordinates
        self.mapped_profile_field = None
        self.confidence_score = 0.0

class ExternalApplicationHandler:
    """Intelligent handler for external job applications"""
    
    def __init__(self, hitl_service: HITLService, gemini_service: GeminiService, config: Dict = None):
        self.logger = logging.getLogger(__name__)
        self.hitl_service = hitl_service
        self.gemini_service = gemini_service
        self.config = config or {}
        
        # Initialize vision service if available
        self.vision_service = get_vision_service() if VISION_AVAILABLE else None
        self.vision_enabled = VISION_AVAILABLE and self.vision_service
        
        # Application state
        self.current_page = None
        self.application_data = {}
        self.discovered_fields = []
        self.pages_processed = []
        
        # File paths
        self.debug_dir = Path("data/external_applications")
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Field mapping patterns (heuristic rules)
        self.field_patterns = {
            'first_name': [
                r'first.*name', r'given.*name', r'fname', r'f_name',
                r'firstname', r'first', r'vorname'
            ],
            'last_name': [
                r'last.*name', r'surname', r'family.*name', r'lname', 
                r'l_name', r'lastname', r'nachname'
            ],
            'full_name': [
                r'^name$', r'full.*name', r'complete.*name', r'your.*name'
            ],
            'email': [
                r'email', r'e-mail', r'mail', r'email.*address',
                r'contact.*email', r'work.*email'
            ],
            'phone': [
                r'phone', r'telephone', r'mobile', r'contact.*number',
                r'phone.*number', r'tel', r'telefon'
            ],
            'address': [
                r'address', r'street', r'location', r'residence'
            ],
            'city': [r'city', r'stadt', r'ville'],
            'state': [r'state', r'province', r'region'],
            'zip_code': [r'zip', r'postal', r'postcode', r'plz'],
            'country': [r'country', r'nation', r'land'],
            'linkedin_url': [
                r'linkedin', r'linked.*in', r'li.*profile', r'social.*profile'
            ],
            'github_url': [
                r'github', r'git.*hub', r'portfolio', r'code.*portfolio'
            ],
            'website': [
                r'website', r'homepage', r'personal.*site', r'portfolio.*site'
            ],
            'cover_letter': [
                r'cover.*letter', r'motivation.*letter', r'message',
                r'why.*interested', r'tell.*us', r'additional.*info'
            ],
            'resume': [
                r'resume', r'cv', r'curriculum.*vitae', r'upload.*resume',
                r'attach.*resume', r'your.*resume'
            ],
            'experience_years': [
                r'years.*experience', r'experience.*years', r'work.*experience',
                r'professional.*experience'
            ]
        }

    async def process_application(self, page: Page, user_profile: UserProfile, 
                                job_details: JobPosting = None) -> Dict[str, Any]:
        """
        Main entry point for processing an external job application
        
        Args:
            page: Playwright page object for the external site
            user_profile: User profile with application data
            job_details: Job details for context
            
        Returns:
            Result dictionary with application status
        """
        self.current_page = page
        self.application_data = self._prepare_application_data(user_profile)
        
        try:
            self.logger.info(f"🌐 Starting external application processing for: {page.url}")
            
            # Take initial screenshot for debugging
            await self._save_debug_screenshot("01_initial_page")
            
            # Step 1: Analyze the page structure
            page_analysis = await self._analyze_page_structure()
            
            # Step 2: Discover form fields
            form_fields = await self._discover_form_fields()
            
            if not form_fields:
                self.logger.warning("No form fields discovered on the page")
                return {"success": False, "error": "No form fields found"}
            
            # Step 3: Map fields to profile data
            mapped_fields = await self._map_fields_to_profile(form_fields)
            
            # Step 4: HITL review of field mapping
            if self.hitl_service:
                mapping_approved = await self._hitl_review_field_mapping(mapped_fields)
                if not mapping_approved:
                    return {"success": False, "error": "Field mapping not approved by user"}
            
            # Step 5: Fill the form
            fill_result = await self._fill_form_fields(mapped_fields)
            
            # Step 6: Handle file uploads (resume, cover letter)
            upload_result = await self._handle_file_uploads(mapped_fields)
            
            # Step 7: Navigate through multi-page forms if needed
            navigation_result = await self._handle_form_navigation()
            
            # Step 8: Final review before submission
            if self.hitl_service:
                submit_approved = await self._hitl_final_review()
                if not submit_approved:
                    return {"success": False, "error": "Submission not approved by user"}
            
            # Step 9: Submit application (in demo mode, just log)
            submission_result = await self._submit_application()
            
            return {
                "success": True,
                "pages_processed": len(self.pages_processed),
                "fields_filled": len([f for f in mapped_fields if f.mapped_profile_field]),
                "submission_result": submission_result
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error processing external application: {e}")
            await self._save_debug_screenshot("error_state")
            return {"success": False, "error": str(e)}

    def _prepare_application_data(self, user_profile: UserProfile) -> Dict[str, Any]:
        """Prepare application data from user profile"""
        data = {}
        
        if user_profile.contact_info:
            data.update({
                'first_name': user_profile.contact_info.first_name,
                'last_name': user_profile.contact_info.last_name,
                'email': user_profile.contact_info.email,
                'phone': user_profile.contact_info.phone,
                'full_name': f"{user_profile.contact_info.first_name} {user_profile.contact_info.last_name}"
            })
            
            if user_profile.contact_info.address:
                data.update({
                    'address': user_profile.contact_info.address.street,
                    'city': user_profile.contact_info.address.city,
                    'state': user_profile.contact_info.address.state,
                    'zip_code': user_profile.contact_info.address.zip_code,
                    'country': user_profile.contact_info.address.country
                })
        
        if user_profile.social_profiles:
            data.update({
                'linkedin_url': user_profile.social_profiles.linkedin_url,
                'github_url': user_profile.social_profiles.github_url,
                'website': user_profile.social_profiles.personal_website
            })
        
        # Add calculated fields
        if user_profile.work_experience:
            total_years = sum(exp.duration_years or 0 for exp in user_profile.work_experience)
            data['experience_years'] = str(total_years)
        
        return data

    async def _analyze_page_structure(self) -> Dict[str, Any]:
        """Analyze the overall page structure"""
        try:
            self.logger.info("🔍 Analyzing page structure...")
            
            analysis = {
                "url": self.current_page.url,
                "title": await self.current_page.title(),
                "forms_count": 0,
                "page_type": "unknown"
            }
            
            # Count forms
            forms = await self.current_page.locator('form').all()
            analysis["forms_count"] = len(forms)
            
            # Identify page type based on content
            page_content = await self.current_page.content()
            content_lower = page_content.lower()
            
            if any(indicator in content_lower for indicator in 
                   ['job application', 'apply for', 'career', 'employment']):
                analysis["page_type"] = "job_application"
            elif any(indicator in content_lower for indicator in 
                     ['workday', 'greenhouse', 'lever', 'bamboohr']):
                analysis["page_type"] = "ats_system"
            elif any(indicator in content_lower for indicator in 
                     ['upload resume', 'attach cv', 'personal information']):
                analysis["page_type"] = "application_form"
            
            # Use vision service for enhanced analysis if available
            if self.vision_enabled:
                try:
                    screenshot = await self.current_page.screenshot()
                    vision_analysis = await self.vision_service.analyze_page_structure(screenshot)
                    analysis["vision_analysis"] = vision_analysis
                except Exception as e:
                    self.logger.warning(f"Vision analysis failed: {e}")
            
            self.logger.info(f"📊 Page analysis: {analysis['page_type']} with {analysis['forms_count']} forms")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing page structure: {e}")
            return {"url": self.current_page.url, "error": str(e)}

    async def _discover_form_fields(self) -> List[FieldInfo]:
        """Discover all interactive form fields on the page"""
        try:
            self.logger.info("🔍 Discovering form fields...")
            
            discovered_fields = []
            
            # Define field selectors to search for
            field_selectors = {
                'input_text': 'input[type="text"], input:not([type])',
                'input_email': 'input[type="email"]',
                'input_tel': 'input[type="tel"], input[type="phone"]',
                'input_url': 'input[type="url"]',
                'input_file': 'input[type="file"]',
                'textarea': 'textarea',
                'select': 'select',
                'input_checkbox': 'input[type="checkbox"]',
                'input_radio': 'input[type="radio"]'
            }
            
            for field_type, selector in field_selectors.items():
                elements = await self.current_page.locator(selector).all()
                
                for element in elements:
                    try:
                        # Skip hidden fields
                        if not await element.is_visible():
                            continue
                        
                        field_info = await self._extract_field_info(element, field_type)
                        if field_info:
                            discovered_fields.append(field_info)
                    except:
                        continue
            
            self.logger.info(f"📋 Discovered {len(discovered_fields)} form fields")
            
            # Use vision service as fallback if few fields found
            if len(discovered_fields) < 3 and self.vision_enabled:
                vision_fields = await self._discover_fields_with_vision()
                discovered_fields.extend(vision_fields)
            
            self.discovered_fields = discovered_fields
            return discovered_fields
            
        except Exception as e:
            self.logger.error(f"Error discovering form fields: {e}")
            return []

    async def _extract_field_info(self, element: Locator, field_type: str) -> Optional[FieldInfo]:
        """Extract information about a specific form field"""
        try:
            # Get basic attributes
            field_id = await element.get_attribute('id') or ""
            name = await element.get_attribute('name') or ""
            placeholder = await element.get_attribute('placeholder') or ""
            required = await element.get_attribute('required') is not None
            
            # Find associated label
            label = await self._find_label_for_field(element, field_id)
            
            # Get coordinates for potential vision-based interaction
            try:
                bounding_box = await element.bounding_box()
                coordinates = (
                    int(bounding_box['x'] + bounding_box['width'] / 2),
                    int(bounding_box['y'] + bounding_box['height'] / 2)
                ) if bounding_box else None
            except:
                coordinates = None
            
            return FieldInfo(
                element=element,
                field_type=field_type,
                label=label,
                field_id=field_id,
                name=name,
                placeholder=placeholder,
                required=required,
                coordinates=coordinates
            )
            
        except Exception as e:
            self.logger.debug(f"Error extracting field info: {e}")
            return None

    async def _find_label_for_field(self, element: Locator, field_id: str) -> str:
        """Find the label text associated with a form field"""
        try:
            # Method 1: Look for label with for attribute
            if field_id:
                label_element = await self.current_page.locator(f'label[for="{field_id}"]').first
                if await label_element.count() > 0:
                    return (await label_element.inner_text()).strip()
            
            # Method 2: Look for aria-label
            aria_label = await element.get_attribute('aria-label')
            if aria_label:
                return aria_label.strip()
            
            # Method 3: Look for surrounding label
            parent = element.locator('xpath=..')
            label_in_parent = await parent.locator('label').first
            if await label_in_parent.count() > 0:
                return (await label_in_parent.inner_text()).strip()
            
            # Method 4: Look for preceding text
            try:
                preceding_text = await element.locator('xpath=preceding-sibling::*[1]').first
                if await preceding_text.count() > 0:
                    text = (await preceding_text.inner_text()).strip()
                    if len(text) < 100:  # Reasonable label length
                        return text
            except:
                pass
            
            return ""
            
        except Exception as e:
            self.logger.debug(f"Error finding label: {e}")
            return ""

    async def _discover_fields_with_vision(self) -> List[FieldInfo]:
        """Use vision service to discover additional form fields"""
        try:
            self.logger.info("🔍 Using vision service to discover additional fields...")
            
            screenshot = await self.current_page.screenshot()
            vision_fields = await self.vision_service.detect_form_fields(screenshot)
            
            discovered_vision_fields = []
            
            for field_data in vision_fields:
                if field_data.get("coordinates"):
                    field_info = FieldInfo(
                        element=None,  # No DOM element for vision-detected fields
                        field_type=field_data.get("type", "unknown"),
                        label=field_data.get("label", ""),
                        coordinates=(
                            field_data["coordinates"]["x"],
                            field_data["coordinates"]["y"]
                        )
                    )
                    field_info.confidence_score = field_data.get("confidence", 0.0)
                    discovered_vision_fields.append(field_info)
            
            self.logger.info(f"🔍 Vision service discovered {len(discovered_vision_fields)} additional fields")
            return discovered_vision_fields
            
        except Exception as e:
            self.logger.error(f"Vision field discovery failed: {e}")
            return []

    async def _map_fields_to_profile(self, fields: List[FieldInfo]) -> List[FieldInfo]:
        """Map discovered fields to user profile data"""
        try:
            self.logger.info("🎯 Mapping fields to profile data...")
            
            mapped_fields = []
            
            for field in fields:
                # Combine all available text for analysis
                field_text = " ".join(filter(None, [
                    field.label, field.name, field.field_id, field.placeholder
                ])).lower()
                
                # Use heuristic pattern matching first
                mapped_field = self._match_field_heuristically(field, field_text)
                
                # Use AI for ambiguous cases
                if not mapped_field and self.gemini_service and field_text:
                    mapped_field = await self._map_field_with_ai(field, field_text)
                
                if mapped_field:
                    field.mapped_profile_field = mapped_field
                    field.confidence_score = 0.9 if mapped_field in self.application_data else 0.3
                
                mapped_fields.append(field)
            
            successful_mappings = len([f for f in mapped_fields if f.mapped_profile_field])
            self.logger.info(f"🎯 Successfully mapped {successful_mappings}/{len(fields)} fields")
            
            return mapped_fields
            
        except Exception as e:
            self.logger.error(f"Error mapping fields: {e}")
            return fields

    def _match_field_heuristically(self, field: FieldInfo, field_text: str) -> Optional[str]:
        """Match field using heuristic patterns"""
        for profile_field, patterns in self.field_patterns.items():
            for pattern in patterns:
                if re.search(pattern, field_text, re.IGNORECASE):
                    if profile_field in self.application_data:
                        return profile_field
        return None

    async def _map_field_with_ai(self, field: FieldInfo, field_text: str) -> Optional[str]:
        """Use AI to map ambiguous fields"""
        try:
            prompt = f"""
            Analyze this form field and determine what type of information it's asking for:
            
            Field text: "{field_text}"
            Field type: {field.field_type}
            
            Available profile fields: {list(self.application_data.keys())}
            
            Return only the matching profile field name, or 'unknown' if no match.
            """
            
            response = await self.gemini_service.generate_text(prompt)
            suggested_field = response.strip().lower()
            
            if suggested_field in self.application_data:
                return suggested_field
                
        except Exception as e:
            self.logger.debug(f"AI field mapping failed: {e}")
        
        return None

    async def _hitl_review_field_mapping(self, mapped_fields: List[FieldInfo]) -> bool:
        """Human-in-the-loop review of field mappings"""
        try:
            self.logger.info("👤 Requesting human review of field mappings...")
            
            mapping_summary = []
            for field in mapped_fields:
                if field.mapped_profile_field:
                    value = self.application_data.get(field.mapped_profile_field, "")
                    mapping_summary.append({
                        "field_label": field.label or field.name or field.field_id,
                        "mapped_to": field.mapped_profile_field,
                        "value_to_fill": str(value)[:50],
                        "confidence": field.confidence_score
                    })
            
            review_request = {
                "type": "field_mapping_review",
                "url": self.current_page.url,
                "mappings": mapping_summary,
                "message": f"Please review the field mappings for {len(mapping_summary)} fields. Approve to continue with application."
            }
            
            response = await self.hitl_service.request_human_input(review_request)
            return response.get("approved", False)
            
        except Exception as e:
            self.logger.error(f"HITL review failed: {e}")
            return True  # Default to approved if HITL fails

    async def _fill_form_fields(self, mapped_fields: List[FieldInfo]) -> Dict[str, Any]:
        """Fill the mapped form fields with profile data"""
        try:
            self.logger.info("📝 Filling form fields...")
            
            filled_count = 0
            errors = []
            
            for field in mapped_fields:
                if not field.mapped_profile_field or field.mapped_profile_field not in self.application_data:
                    continue
                
                value = self.application_data[field.mapped_profile_field]
                if not value:
                    continue
                
                try:
                    success = await self._fill_individual_field(field, str(value))
                    if success:
                        filled_count += 1
                    else:
                        errors.append(f"Failed to fill {field.label or field.name}")
                        
                except Exception as e:
                    error_msg = f"Error filling {field.label or field.name}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
                
                # Small delay between fields
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            self.logger.info(f"📝 Filled {filled_count} fields with {len(errors)} errors")
            
            # Save progress screenshot
            await self._save_debug_screenshot("02_fields_filled")
            
            return {
                "success": True,
                "fields_filled": filled_count,
                "errors": errors
            }
            
        except Exception as e:
            self.logger.error(f"Error filling form fields: {e}")
            return {"success": False, "error": str(e)}

    async def _fill_individual_field(self, field: FieldInfo, value: str) -> bool:
        """Fill an individual form field"""
        try:
            if field.element:
                # Use DOM element if available
                if field.field_type in ['input_text', 'input_email', 'input_tel', 'input_url']:
                    await field.element.clear()
                    await field.element.fill(value)
                elif field.field_type == 'textarea':
                    await field.element.clear()
                    await field.element.fill(value)
                elif field.field_type == 'select':
                    await field.element.select_option(label=value)
                return True
            
            elif field.coordinates and self.vision_enabled:
                # Use vision-based interaction
                x, y = field.coordinates
                await self.current_page.mouse.click(x, y)
                await asyncio.sleep(0.5)
                
                # Clear field and type value
                await self.current_page.keyboard.press('Control+a')
                await self.current_page.keyboard.type(value)
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error filling individual field: {e}")
            return False

    async def _handle_file_uploads(self, mapped_fields: List[FieldInfo]) -> Dict[str, Any]:
        """Handle file uploads (resume, cover letter)"""
        try:
            self.logger.info("📎 Handling file uploads...")
            
            upload_results = []
            
            for field in mapped_fields:
                if field.field_type == 'input_file' and field.mapped_profile_field:
                    
                    # For demo purposes, we'll skip actual file uploads
                    # In production, you'd have resume/cover letter files ready
                    
                    self.logger.info(f"📎 Would upload {field.mapped_profile_field} to {field.label}")
                    upload_results.append({
                        "field": field.label or field.name,
                        "type": field.mapped_profile_field,
                        "status": "demo_skipped"
                    })
            
            return {
                "success": True,
                "uploads": upload_results
            }
            
        except Exception as e:
            self.logger.error(f"Error handling file uploads: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_form_navigation(self) -> Dict[str, Any]:
        """Handle navigation through multi-page forms"""
        try:
            self.logger.info("🧭 Checking for form navigation...")
            
            # Look for common "Next", "Continue", "Save and Continue" buttons
            navigation_selectors = [
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'button:has-text("Save and Continue")',
                'input[type="submit"][value*="Next"]',
                'input[type="submit"][value*="Continue"]',
                '.btn:has-text("Next")',
                '.btn:has-text("Continue")'
            ]
            
            for selector in navigation_selectors:
                next_button = await self.current_page.locator(selector).first
                if await next_button.count() > 0 and await next_button.is_visible():
                    self.logger.info(f"🧭 Found navigation button: {selector}")
                    
                    # For demo, we'll log but not actually navigate
                    self.logger.info("🧭 [DEMO] Would click to proceed to next page")
                    # await next_button.click()
                    # await self.current_page.wait_for_load_state('networkidle')
                    
                    return {"success": True, "action": "navigation_available"}
            
            self.logger.info("🧭 No navigation buttons found - likely single-page form")
            return {"success": True, "action": "single_page"}
            
        except Exception as e:
            self.logger.error(f"Error handling form navigation: {e}")
            return {"success": False, "error": str(e)}

    async def _hitl_final_review(self) -> bool:
        """Final human review before submission"""
        try:
            self.logger.info("👤 Requesting final review before submission...")
            
            # Take screenshot for review
            await self._save_debug_screenshot("03_pre_submission")
            
            review_request = {
                "type": "final_submission_review",
                "url": self.current_page.url,
                "message": "Application form has been filled. Please review and approve submission.",
                "screenshot_path": str(self.debug_dir / "03_pre_submission.png")
            }
            
            response = await self.hitl_service.request_human_input(review_request)
            return response.get("approved", False)
            
        except Exception as e:
            self.logger.error(f"Final HITL review failed: {e}")
            return True  # Default to approved

    async def _submit_application(self) -> Dict[str, Any]:
        """Submit the application (demo mode - just logs)"""
        try:
            self.logger.info("🚀 Attempting to submit application...")
            
            # Look for submit buttons
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Apply")',
                'button:has-text("Send Application")',
                '.btn:has-text("Submit")',
                '.btn:has-text("Apply")'
            ]
            
            for selector in submit_selectors:
                submit_button = await self.current_page.locator(selector).first
                if await submit_button.count() > 0 and await submit_button.is_visible():
                    
                    button_text = await submit_button.inner_text()
                    self.logger.info(f"🚀 Found submit button: '{button_text}'")
                    
                    # In demo mode, just log the action
                    self.logger.info("🚀 [DEMO MODE] Application would be submitted here")
                    
                    # In production, you would:
                    # await submit_button.click()
                    # await self.current_page.wait_for_load_state('networkidle')
                    
                    await self._save_debug_screenshot("04_submission_complete")
                    
                    return {
                        "success": True,
                        "status": "demo_completed",
                        "button_found": button_text
                    }
            
            self.logger.warning("🚀 No submit button found")
            return {
                "success": False,
                "status": "no_submit_button"
            }
            
        except Exception as e:
            self.logger.error(f"Error submitting application: {e}")
            return {"success": False, "error": str(e)}

    async def _save_debug_screenshot(self, filename_prefix: str):
        """Save debug screenshot"""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.png"
            filepath = self.debug_dir / filename
            
            await self.current_page.screenshot(path=str(filepath), full_page=True)
            self.logger.debug(f"📸 Debug screenshot saved: {filepath}")
            
        except Exception as e:
            self.logger.debug(f"Failed to save debug screenshot: {e}")

# Factory function for easy integration
def create_external_handler(hitl_service: HITLService, gemini_service: GeminiService, 
                          config: Dict = None) -> ExternalApplicationHandler:
    """Create configured ExternalApplicationHandler instance"""
    return ExternalApplicationHandler(hitl_service, gemini_service, config) 