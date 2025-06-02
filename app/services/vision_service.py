#!/usr/bin/env python3
"""
🔍 Vision Service using Ollama with Gemma 3-1B Vision Model
Provides vision-based UI interaction capabilities for web automation
"""

import asyncio
import base64
import json
import logging
from typing import Dict, List, Optional, Tuple, Union
import aiohttp
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class VisionService:
    """Vision service using Ollama with smallest Gemma 3 vision model"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model_name = "gemma3:1b"  # Latest Gemma 3 1B model - smallest and most efficient
        self.vision_model = "llava:latest"  # For multimodal tasks
        self.initialized = False
        
    async def initialize(self):
        """Initialize and ensure models are available"""
        try:
            # Check if Ollama is running
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    if response.status != 200:
                        raise Exception("Ollama server not accessible")
                    
                    models = await response.json()
                    available_models = [model['name'] for model in models.get('models', [])]
                    
                    # Ensure vision model is available
                    if self.vision_model not in available_models:
                        logger.info(f"Pulling {self.vision_model} model...")
                        await self._pull_model(self.vision_model)
                    
                    self.initialized = True
                    logger.info("🔍 Vision service initialized with Gemma vision models")
                    
        except Exception as e:
            logger.error(f"Failed to initialize vision service: {e}")
            raise
    
    async def _pull_model(self, model_name: str):
        """Pull a model if not available"""
        async with aiohttp.ClientSession() as session:
            data = {"name": model_name}
            async with session.post(f"{self.ollama_url}/api/pull", json=data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to pull model {model_name}")
                    
                # Wait for pull to complete
                async for line in response.content:
                    if line:
                        status = json.loads(line.decode())
                        if status.get('status') == 'success':
                            break
    
    async def analyze_image_for_element(
        self, 
        image_bytes: bytes, 
        element_description: str,
        page_context: str = ""
    ) -> Optional[Dict]:
        """
        Analyze image to find a specific UI element
        
        Args:
            image_bytes: Screenshot as bytes
            element_description: Description of element to find (e.g., "Date posted filter button")
            page_context: Additional context about the page
            
        Returns:
            Dict with coordinates: {"x": int, "y": int, "width": int, "height": int, "confidence": float}
            or None if not found
        """
        if not self.initialized:
            await self.initialize()
        
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create detailed prompt for element location
        prompt = f"""
You are analyzing a LinkedIn job search page screenshot. 

Task: Find the "{element_description}" element and provide its precise location.

Context: {page_context}

Instructions:
1. Look for the exact element described: "{element_description}"
2. Consider text labels, button styles, and UI patterns typical of LinkedIn
3. Provide the bounding box coordinates as JSON

Response format (only return this JSON, no other text):
{{"x": <left_pixel>, "y": <top_pixel>, "width": <width_pixels>, "height": <height_pixels>, "confidence": <0.0-1.0>, "found": <true/false>}}

If element not found, return: {{"found": false}}
"""

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                }
                
                async with session.post(f"{self.ollama_url}/api/generate", json=data) as response:
                    if response.status != 200:
                        logger.error(f"Vision API request failed: {response.status}")
                        return None
                    
                    result = await response.json()
                    response_text = result.get('response', '').strip()
                    
                    # Try to parse JSON response
                    try:
                        # Extract JSON from response
                        if '{' in response_text and '}' in response_text:
                            json_start = response_text.find('{')
                            json_end = response_text.rfind('}') + 1
                            json_str = response_text[json_start:json_end]
                            element_info = json.loads(json_str)
                            
                            if element_info.get('found', False):
                                logger.info(f"🎯 Vision found '{element_description}': {element_info}")
                                return element_info
                            else:
                                logger.warning(f"🔍 Vision could not find '{element_description}'")
                                return None
                        else:
                            logger.warning(f"🔍 Vision response not in expected JSON format: {response_text}")
                            return None
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse vision response JSON: {e}")
                        logger.error(f"Raw response: {response_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return None
    
    async def find_clickable_elements(
        self, 
        image_bytes: bytes, 
        element_types: List[str] = None
    ) -> List[Dict]:
        """
        Find all clickable elements of specified types in the image
        
        Args:
            image_bytes: Screenshot as bytes
            element_types: List of element types to find (e.g., ["button", "link", "dropdown"])
            
        Returns:
            List of elements with coordinates and descriptions
        """
        if not self.initialized:
            await self.initialize()
        
        if element_types is None:
            element_types = ["button", "link", "dropdown", "checkbox", "radio button"]
        
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = f"""
Analyze this LinkedIn page screenshot and identify all clickable elements.

Find these types of elements: {', '.join(element_types)}

For each clickable element found, provide:
1. Element type (button, link, etc.)
2. Visible text or label
3. Bounding box coordinates
4. Purpose/function description

Return as JSON array:
[
  {{"type": "button", "text": "Date posted", "x": 123, "y": 456, "width": 100, "height": 30, "description": "Filter by date posted"}},
  ...
]

Only return the JSON array, no other text.
"""

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                }
                
                async with session.post(f"{self.ollama_url}/api/generate", json=data) as response:
                    if response.status != 200:
                        return []
                    
                    result = await response.json()
                    response_text = result.get('response', '').strip()
                    
                    try:
                        # Extract JSON array from response
                        if '[' in response_text and ']' in response_text:
                            json_start = response_text.find('[')
                            json_end = response_text.rfind(']') + 1
                            json_str = response_text[json_start:json_end]
                            elements = json.loads(json_str)
                            
                            logger.info(f"🔍 Vision found {len(elements)} clickable elements")
                            return elements
                        else:
                            logger.warning("No JSON array found in vision response")
                            return []
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse clickable elements JSON: {e}")
                        return []
                        
        except Exception as e:
            logger.error(f"Failed to find clickable elements: {e}")
            return []
    
    async def analyze_form_fields(self, image_bytes: bytes) -> List[Dict]:
        """
        Analyze image to identify form fields and their types
        
        Returns:
            List of form fields with metadata
        """
        if not self.initialized:
            await self.initialize()
        
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = """
Analyze this form/application screenshot and identify all form fields.

For each form field, determine:
1. Field type (text input, textarea, select dropdown, checkbox, radio, file upload)
2. Label or placeholder text
3. Whether it appears required (marked with * or "required")
4. Bounding box coordinates
5. Current value if visible

Return as JSON array:
[
  {
    "type": "text_input",
    "label": "First Name",
    "required": true,
    "x": 100, "y": 200, "width": 250, "height": 40,
    "placeholder": "Enter your first name",
    "current_value": ""
  },
  ...
]

Only return the JSON array.
"""

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                }
                
                async with session.post(f"{self.ollama_url}/api/generate", json=data) as response:
                    if response.status != 200:
                        return []
                    
                    result = await response.json()
                    response_text = result.get('response', '').strip()
                    
                    try:
                        if '[' in response_text and ']' in response_text:
                            json_start = response_text.find('[')
                            json_end = response_text.rfind(']') + 1
                            json_str = response_text[json_start:json_end]
                            fields = json.loads(json_str)
                            
                            logger.info(f"📝 Vision identified {len(fields)} form fields")
                            return fields
                        else:
                            return []
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse form fields JSON: {e}")
                        return []
                        
        except Exception as e:
            logger.error(f"Failed to analyze form fields: {e}")
            return []
    
    async def get_element_center(self, element_info: Dict) -> Tuple[int, int]:
        """Get center coordinates of an element"""
        if not element_info or not element_info.get('found', True):
            return None, None
        
        x = element_info.get('x', 0)
        y = element_info.get('y', 0)
        width = element_info.get('width', 0)
        height = element_info.get('height', 0)
        
        center_x = x + width // 2
        center_y = y + height // 2
        
        return center_x, center_y
    
    async def verify_page_state(self, image_bytes: bytes, expected_state: str) -> bool:
        """
        Verify if the page is in an expected state
        
        Args:
            image_bytes: Screenshot as bytes
            expected_state: Description of expected page state
            
        Returns:
            True if page matches expected state
        """
        if not self.initialized:
            await self.initialize()
        
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = f"""
Analyze this screenshot and determine if the page state matches this description:
"{expected_state}"

Consider:
- Visible elements and their states
- Page content and layout
- Any loading indicators or overlays
- Error messages or success indicators

Respond with only: {{"matches": true}} or {{"matches": false}}
"""

        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                }
                
                async with session.post(f"{self.ollama_url}/api/generate", json=data) as response:
                    if response.status != 200:
                        return False
                    
                    result = await response.json()
                    response_text = result.get('response', '').strip()
                    
                    try:
                        if '{' in response_text and '}' in response_text:
                            json_start = response_text.find('{')
                            json_end = response_text.rfind('}') + 1
                            json_str = response_text[json_start:json_end]
                            state_info = json.loads(json_str)
                            
                            return state_info.get('matches', False)
                        else:
                            return False
                            
                    except json.JSONDecodeError:
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to verify page state: {e}")
            return False

# Global vision service instance
vision_service = VisionService() 