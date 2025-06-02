#!/usr/bin/env python3
"""
🔍 Vision Service - Computer Vision Integration with Ollama
Provides AI-powered visual analysis for robust web automation
"""

import httpx
import base64
import json
import logging
from typing import Dict, Optional, List, Tuple, Any
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class VisionService:
    """AI-powered computer vision service using Ollama multimodal models"""
    
    def __init__(self, 
                 ollama_api_url: str = "http://localhost:11434",
                 model_name: str = "llava:latest",
                 timeout: float = 120.0):
        self.ollama_api_url = ollama_api_url
        self.model_name = model_name
        self.timeout = timeout
        self.screenshot_dir = Path("data/screenshots/vision_analysis")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
    async def check_ollama_availability(self) -> bool:
        """Check if Ollama is running and the model is available"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.ollama_api_url}/api/tags")
                if response.status_code != 200:
                    return False
                
                # Check if our model is available
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                if not any(self.model_name in name for name in model_names):
                    logger.warning(f"Model {self.model_name} not found. Available models: {model_names}")
                    # Try to pull the model
                    logger.info(f"Attempting to pull model {self.model_name}...")
                    pull_response = await client.post(
                        f"{self.ollama_api_url}/api/pull",
                        json={"name": self.model_name}
                    )
                    if pull_response.status_code != 200:
                        return False
                
                return True
        except Exception as e:
            logger.error(f"Ollama availability check failed: {e}")
            return False
    
    async def analyze_image_with_prompt(self, 
                                      image_bytes: bytes, 
                                      prompt: str,
                                      expect_json: bool = True,
                                      save_debug_image: bool = True) -> Optional[Dict[str, Any]]:
        """
        Send an image and prompt to Ollama for visual analysis
        
        Args:
            image_bytes: Raw image data
            prompt: Analysis prompt for the model
            expect_json: Whether to expect JSON response
            save_debug_image: Save image for debugging
            
        Returns:
            Analysis result or None if failed
        """
        try:
            # Save debug image if requested
            if save_debug_image:
                debug_path = self.screenshot_dir / f"analysis_{len(list(self.screenshot_dir.glob('*.png')))}.png"
                with open(debug_path, 'wb') as f:
                    f.write(image_bytes)
                logger.debug(f"Debug image saved: {debug_path}")
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Prepare payload for Ollama
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False
            }
            
            logger.info(f"Sending image to Ollama ({self.model_name}) with prompt: {prompt[:100]}...")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_api_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                response_json = response.json()
                llm_output = response_json.get('response', '')
                
                logger.info(f"Ollama response: {llm_output[:200]}...")
                
                if expect_json:
                    try:
                        # Try to parse as JSON
                        parsed_result = json.loads(llm_output)
                        return {"success": True, "data": parsed_result, "raw_response": llm_output}
                    except json.JSONDecodeError:
                        logger.warning(f"Expected JSON but got text: {llm_output}")
                        return {"success": False, "data": None, "raw_response": llm_output}
                else:
                    return {"success": True, "data": llm_output, "raw_response": llm_output}
                
        except httpx.RequestError as e:
            logger.error(f"HTTP request to Ollama failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing image with Ollama: {e}")
            return None
    
    async def find_element_coordinates(self, 
                                     image_bytes: bytes, 
                                     element_description: str) -> Optional[Dict[str, int]]:
        """
        Find an element's coordinates in an image
        
        Args:
            image_bytes: Screenshot data
            element_description: Description of what to find
            
        Returns:
            Coordinates dict with x, y, width, height or None
        """
        prompt = f"""
        Find the {element_description} in this screenshot.
        
        Respond ONLY with a JSON object containing the bounding box coordinates:
        {{"x": center_x, "y": center_y, "width": width, "height": height}}
        
        If the element is not found, respond with: {{"found": false}}
        
        Be precise with coordinates. Use the center point for clicking.
        """
        
        result = await self.analyze_image_with_prompt(image_bytes, prompt, expect_json=True)
        
        if result and result.get("success") and result.get("data"):
            data = result["data"]
            if data.get("found") is False:
                return None
            if all(key in data for key in ["x", "y"]):
                return data
        
        return None
    
    async def detect_form_fields(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Detect all form fields in an image
        
        Returns:
            List of detected form fields with their positions and types
        """
        prompt = """
        Analyze this screenshot and identify ALL form input fields, buttons, and interactive elements.
        
        For each element found, provide:
        - type: "input", "button", "select", "textarea", "checkbox", "radio"
        - label: the associated label text or placeholder
        - coordinates: center x,y for clicking
        - text: any visible text on/in the element
        
        Respond with a JSON array:
        [
          {
            "type": "input",
            "label": "Email Address",
            "coordinates": {"x": 100, "y": 200},
            "text": "email@example.com",
            "confidence": 0.9
          }
        ]
        
        If no form elements found, respond with: []
        """
        
        result = await self.analyze_image_with_prompt(image_bytes, prompt, expect_json=True)
        
        if result and result.get("success") and result.get("data"):
            return result["data"] if isinstance(result["data"], list) else []
        
        return []
    
    async def read_text_at_coordinates(self, 
                                     image_bytes: bytes, 
                                     x: int, y: int, 
                                     width: int = 100, 
                                     height: int = 50) -> Optional[str]:
        """
        Read text at specific coordinates in an image
        
        Args:
            image_bytes: Screenshot data
            x, y: Center coordinates of text area
            width, height: Approximate size of text area
            
        Returns:
            Extracted text or None
        """
        prompt = f"""
        Look at the region around coordinates ({x}, {y}) in this screenshot.
        The text area is approximately {width}x{height} pixels.
        
        Extract ONLY the text from this specific region.
        Respond with just the text, no additional formatting or explanation.
        
        If no readable text is found, respond with: "NO_TEXT_FOUND"
        """
        
        result = await self.analyze_image_with_prompt(image_bytes, prompt, expect_json=False)
        
        if result and result.get("success"):
            text = result.get("data", "").strip()
            return text if text != "NO_TEXT_FOUND" else None
        
        return None
    
    async def detect_modal_or_popup(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Detect if there's a modal, popup, or overlay in the image
        
        Returns:
            Detection result with modal info
        """
        prompt = """
        Analyze this screenshot for modal dialogs, popups, overlays, or blocking elements.
        
        Look for:
        - Dialog boxes with dark overlay background
        - Popup windows
        - Alert messages
        - Forms that appear on top of content
        - "Easy Apply" modals or job application forms
        
        Respond with JSON:
        {
          "modal_detected": true/false,
          "modal_type": "dialog|popup|overlay|form|alert",
          "title": "modal title text if visible",
          "close_button": {"x": 100, "y": 50} or null,
          "primary_action": {"text": "Apply", "x": 200, "y": 300} or null,
          "confidence": 0.0-1.0
        }
        """
        
        result = await self.analyze_image_with_prompt(image_bytes, prompt, expect_json=True)
        
        if result and result.get("success") and result.get("data"):
            return result["data"]
        
        return {"modal_detected": False, "confidence": 0.0}
    
    async def solve_simple_captcha(self, image_bytes: bytes) -> Optional[str]:
        """
        Attempt to solve simple text-based CAPTCHAs
        
        Args:
            image_bytes: CAPTCHA image data
            
        Returns:
            CAPTCHA solution text or None
        """
        prompt = """
        This is a CAPTCHA image. Extract the characters/text shown.
        
        Rules:
        - Look for letters, numbers, or simple text
        - Ignore distorted backgrounds
        - Focus on the main text content
        - Be case-sensitive if obvious
        
        Respond ONLY with the characters you see, no spaces or formatting.
        If you cannot read the text clearly, respond with: "UNREADABLE"
        """
        
        result = await self.analyze_image_with_prompt(image_bytes, prompt, expect_json=False)
        
        if result and result.get("success"):
            text = result.get("data", "").strip()
            return text if text != "UNREADABLE" else None
        
        return None
    
    async def analyze_page_structure(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze the overall structure and layout of a webpage
        
        Returns:
            Page analysis with main sections and navigation elements
        """
        prompt = """
        Analyze this webpage screenshot and identify its main structure.
        
        Identify:
        - Navigation elements (header, menu, breadcrumbs)
        - Main content areas
        - Sidebar elements
        - Footer
        - Forms or input areas
        - Call-to-action buttons
        - Job listings or cards (if present)
        
        Respond with JSON:
        {
          "page_type": "job_board|company_careers|application_form|profile|search_results",
          "main_sections": [
            {
              "type": "navigation|content|sidebar|footer|form",
              "description": "brief description",
              "coordinates": {"x": 100, "y": 200, "width": 300, "height": 400}
            }
          ],
          "interactive_elements": [
            {
              "type": "button|link|input|select",
              "text": "element text",
              "coordinates": {"x": 100, "y": 200}
            }
          ],
          "confidence": 0.0-1.0
        }
        """
        
        result = await self.analyze_image_with_prompt(image_bytes, prompt, expect_json=True)
        
        if result and result.get("success") and result.get("data"):
            return result["data"]
        
        return {"page_type": "unknown", "main_sections": [], "interactive_elements": [], "confidence": 0.0}

# Factory function for easy integration
def get_vision_service(
    ollama_url: str = "http://localhost:11434",
    model: str = "llava:latest"
) -> VisionService:
    """Get configured VisionService instance"""
    return VisionService(ollama_api_url=ollama_url, model_name=model)

# Utility functions for common vision tasks
async def quick_element_find(page, element_description: str) -> Optional[Tuple[int, int]]:
    """
    Quick utility to find an element visually and return click coordinates
    
    Args:
        page: Playwright page object
        element_description: What to look for
        
    Returns:
        (x, y) coordinates for clicking or None
    """
    try:
        vision_service = get_vision_service()
        
        if not await vision_service.check_ollama_availability():
            logger.warning("Ollama not available for visual analysis")
            return None
        
        screenshot = await page.screenshot()
        coordinates = await vision_service.find_element_coordinates(screenshot, element_description)
        
        if coordinates and "x" in coordinates and "y" in coordinates:
            return (coordinates["x"], coordinates["y"])
        
        return None
    except Exception as e:
        logger.error(f"Quick element find failed: {e}")
        return None

async def visual_form_analysis(page) -> List[Dict[str, Any]]:
    """
    Quick utility to analyze form fields visually
    
    Args:
        page: Playwright page object
        
    Returns:
        List of detected form fields
    """
    try:
        vision_service = get_vision_service()
        
        if not await vision_service.check_ollama_availability():
            logger.warning("Ollama not available for visual analysis")
            return []
        
        screenshot = await page.screenshot()
        fields = await vision_service.detect_form_fields(screenshot)
        
        return fields
    except Exception as e:
        logger.error(f"Visual form analysis failed: {e}")
        return [] 