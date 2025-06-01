# Gemini Service - Google Gemini AI integration 
import google.generativeai as genai
from typing import Optional
from config import settings
from app.models.gemini_interaction_models import GeminiRequest, GeminiResponse, GeminiPromptPart
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not configured for GeminiService.")
            # This service is critical for AI features, so we might want to raise an error
            # if the key is missing, preventing instantiation.
            raise ValueError("GEMINI_API_KEY is required for GeminiService to function.")
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            logger.info("Gemini API configured successfully.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini API: {e}", exc_info=True)
            raise ValueError(f"Gemini API configuration failed: {e}")

        # For MVP, we can use a default model. This can be made configurable later.
        self.default_text_model_name = "gemini-1.5-flash-latest"  # Cost-effective and fast for text tasks

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_content(self, request: GeminiRequest) -> GeminiResponse:
        """
        Generates content using the specified Gemini model and prompt.
        Handles retries for transient errors.
        """
        try:
            model_name_to_use = request.model_name or self.default_text_model_name
            model = genai.GenerativeModel(model_name_to_use)
            
            # Constructing the prompt parts for the API call
            # For text-only, this will be a list of strings.
            # If using multimodal later, prompt_parts would contain dicts like {'text': ..., 'inline_data': ...}
            
            prompt_content = [part.text for part in request.prompt_parts if part.text is not None]
            if not prompt_content:
                logger.warning("No text content found in prompt_parts for Gemini request.")
                return GeminiResponse(error_message="Prompt content is empty.")

            logger.info(f"Sending request to Gemini model: {model_name_to_use} with prompt starting: '{prompt_content[0][:100]}...'")

            # GenerationConfig mapping
            generation_config_api = None
            if request.generation_config:
                generation_config_api = genai.types.GenerationConfig(**request.generation_config)

            # SafetySettings mapping
            safety_settings_api = None
            if request.safety_settings:
                safety_settings_api = [
                    genai.types.SafetySetting(category=s['category'], threshold=s['threshold'])
                    for s in request.safety_settings
                ]
            
            response = model.generate_content(
                prompt_content,  # For gemini-1.5-flash, this should be a list of strings or Parts
                generation_config=generation_config_api,
                safety_settings=safety_settings_api
                # stream=False # Default
            )
            
            text_response = None
            try:
                text_response = response.text
            except ValueError:  # Handles cases where response.text might not be directly accessible (e.g. blocked)
                logger.warning("Could not directly access response.text. Checking for prompt feedback.")
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason_msg = f"Content generation blocked. Reason: {response.prompt_feedback.block_reason.name}"
                    logger.warning(block_reason_msg)
                    return GeminiResponse(error_message=block_reason_msg, finish_reason=response.prompt_feedback.block_reason.name)
                # If not blocked but no text, it's an unusual state
                logger.error("Gemini response did not contain text and was not explicitly blocked.")
                return GeminiResponse(error_message="Gemini response did not contain usable text.", finish_reason="UNKNOWN")

            # Attempt to get token count if available (structure might vary)
            # token_count = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
            
            # Finish reason (simplified for now)
            finish_reason_str = "COMPLETED"
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                finish_reason_str = response.prompt_feedback.block_reason.name
            elif not text_response and not (response.prompt_feedback and response.prompt_feedback.block_reason):
                # This case indicates that the response might be empty for other reasons,
                # e.g. max_output_tokens reached with no valid output, or unusual API behavior.
                # The model.generate_content should ideally raise an error for most non-successful terminal states
                # that aren't safety blocks if it can't produce `response.text`.
                # If `response.text` is empty but no block, it might be a valid empty generation.
                # We depend on `response.text` for `text_content`.
                pass

            logger.info(f"Received response from Gemini. Finish reason: {finish_reason_str}")
            return GeminiResponse(
                text_content=text_response,
                finish_reason=finish_reason_str
                # token_count=token_count # Add when token counting is robustly implemented
            )

        except RetryError as re:  # This is if all tenacity retries fail
            logger.error(f"Gemini API call failed after multiple retries: {re.last_attempt.exception()}", exc_info=True)
            return GeminiResponse(error_message=f"API call failed after retries: {re.last_attempt.exception()}")
        except Exception as e:
            logger.error(f"Error during Gemini API call: {e}", exc_info=True)
            # For tenacity to retry, it needs the original exception.
            # If we are not within a tenacity @retry block here (e.g. direct call outside test),
            # we should return a GeminiResponse with error.
            # Since the @retry is on the method, this `raise` will be caught by tenacity.
            raise

    def get_job_relevance_score(self, job_description: str, user_target_role: str) -> Optional[int]:
        """
        Gets a relevance score (1-5) for a job description based on a user's target role using Gemini.
        """
        if not job_description or not user_target_role:
            logger.warning("Job description or user target role is empty for relevance scoring.")
            return None

        prompt_text = (
            f"Analyze the following job description and determine its relevance for a candidate who is a '{user_target_role}'. "
            f"Respond with a single integer score from 1 (not relevant) to 5 (highly relevant). Do not add any other text or explanation. "
            f"Score only.\n\n"
            f"Job Description:\n\"\"\"\n{job_description[:2000]}\n\"\"\""  # Truncate for very long descriptions
        )
        
        request = GeminiRequest(
            model_name=self.default_text_model_name,  # Explicitly provide the model name
            prompt_parts=[GeminiPromptPart(text=prompt_text)],
            generation_config={"temperature": 0.2, "max_output_tokens": 10}  # Low temp for consistent scoring, few tokens
        )
        
        response = self.generate_content(request)
        
        if response.error_message or not response.text_content:
            logger.error(f"Failed to get relevance score from Gemini. Error: {response.error_message}")
            return None
            
        try:
            score_text = response.text_content.strip()
            # Try to extract the first digit found if there's extra text, despite instructions
            import re
            match = re.search(r'\d+', score_text)
            if match:
                score = int(match.group(0))
                if 1 <= score <= 5:
                    logger.info(f"Gemini relevance score for role '{user_target_role}' is: {score}")
                    return score
                else:
                    logger.warning(f"Gemini returned an out-of-range score: {score}. Original text: '{score_text}'")
            else:
                logger.warning(f"Could not parse score from Gemini response: '{score_text}'")
            return None
        except ValueError:
            logger.error(f"Could not parse score '{response.text_content.strip()}' as integer.", exc_info=True)
            return None

if __name__ == "__main__":
    import sys
    import os
    # Add project root to path for testing
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, project_root)
    
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    if not settings.GEMINI_API_KEY:
        print("Cannot run GeminiService direct test: GEMINI_API_KEY not set in .env")
        print("Please add GEMINI_API_KEY=your_api_key_here to your .env file")
    else:
        try:
            gemini_service = GeminiService()
            
            # Test 1: Simple content generation
            print("\n--- Test 1: Simple content generation ---")
            simple_request = GeminiRequest(
                prompt_parts=[GeminiPromptPart(text="What is the primary color of the sky on a clear day? Respond with one word.")],
                generation_config={"temperature": 0.7, "max_output_tokens": 50}
            )
            simple_response = gemini_service.generate_content(simple_request)
            if simple_response.error_message:
                print(f"Test 1 Failed. Error: {simple_response.error_message}")
            else:
                print(f"Test 1 Response: {simple_response.text_content}")

            # Test 2: Job relevance scoring
            print("\n--- Test 2: Job relevance scoring ---")
            sample_jd = """
            We are seeking a Senior Software Engineer with 5+ years of experience in Python, Django, and REST APIs. 
            The ideal candidate will have a strong understanding of microservices architecture and cloud platforms like AWS. 
            Responsibilities include designing, developing, and deploying scalable backend services.
            Experience with PostgreSQL and Docker is a plus. Bachelor's degree in CS or related field required.
            """
            target_role = "Python Backend Developer"
            relevance_score = gemini_service.get_job_relevance_score(sample_jd, target_role)
            if relevance_score is not None:
                print(f"Test 2: Relevance score for '{target_role}' is: {relevance_score}")
            else:
                print(f"Test 2 Failed: Could not get relevance score.")

            # Test 3: Relevance scoring with a less relevant role
            print("\n--- Test 3: Job relevance scoring (less relevant) ---")
            target_role_less_relevant = "Frontend UX Designer"
            relevance_score_less = gemini_service.get_job_relevance_score(sample_jd, target_role_less_relevant)
            if relevance_score_less is not None:
                print(f"Test 3: Relevance score for '{target_role_less_relevant}' is: {relevance_score_less}")
            else:
                print(f"Test 3 Failed: Could not get relevance score for less relevant role.")

        except ValueError as ve:
            print(f"Error initializing GeminiService for tests: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred during GeminiService tests: {e}")
    
    print("\nGeminiService testing completed.") 