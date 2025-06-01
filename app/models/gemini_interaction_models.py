# Gemini Interaction Models - Data structures for AI interactions 
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# In Phase 2, GeminiPromptPart was defined with 'text: Optional[str] = None'
# and a comment about 'inline_data: Optional[Blob]' for multimodal later.
# We'll stick to the text part for now as per the MVP/Phase 2 definition.
class GeminiPromptPart(BaseModel):
    text: Optional[str] = None
    # Example for future:
    # mime_type: Optional[str] = None # e.g., "image/png"
    # data: Optional[bytes] = None # For actual image data

class GeminiRequest(BaseModel):
    model_name: str = Field(..., example="gemini-1.5-pro-latest") # e.g., "gemini-1.5-pro-latest", "gemini-1.5-flash-latest"
    prompt_parts: List[GeminiPromptPart]
    generation_config: Optional[Dict[str, Any]] = Field(None, example={"temperature": 0.7, "max_output_tokens": 2048})
    safety_settings: Optional[List[Dict[str, str]]] = Field(None, example=[
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
    ])
    # For future consideration if using tools/function calling with Gemini
    # tools: Optional[List[Dict[str, Any]]] = None 

class GeminiResponse(BaseModel):
    text_content: Optional[str] = Field(None, example="This is the AI generated response.")
    # The plan mentioned 'candidates: Optional[List[Any]]' for full API response if needed.
    # For simplicity and focus on text, we can omit it or keep it commented for now.
    # candidates: Optional[List[Dict[str, Any]]] = None 
    error_message: Optional[str] = Field(None, example="API call failed due to quota issues.")
    finish_reason: Optional[str] = Field(None, example="STOP") # e.g., STOP, MAX_TOKENS, SAFETY, RECITATION, OTHER
    token_count: Optional[int] = Field(None, example=120) # If available from API usage metadata

    class Config:
        json_schema_extra = {
            "example": {
                "text_content": "The primary benefit of using LLMs in this context is enhanced efficiency.",
                "finish_reason": "STOP",
                "token_count": 45
            }
        }

if __name__ == '__main__':
    # Example Usage
    sample_request = GeminiRequest(
        model_name="gemini-1.5-flash-latest",
        prompt_parts=[
            GeminiPromptPart(text="Explain the concept of prompt engineering in one sentence."),
        ],
        generation_config={"temperature": 0.5, "max_output_tokens": 100}
    )
    print("Sample GeminiRequest:")
    print(sample_request.model_dump_json(indent=2))

    sample_response = GeminiResponse(
        text_content="Prompt engineering is the art of crafting effective inputs to guide large language models toward desired outputs.",
        finish_reason="STOP",
        token_count=25
    )
    print("\nSample GeminiResponse:")
    print(sample_response.model_dump_json(indent=2))

    error_response = GeminiResponse(
        error_message="API key invalid.",
        finish_reason="ERROR"
    )
    print("\nSample Error GeminiResponse:")
    print(error_response.model_dump_json(indent=2)) 