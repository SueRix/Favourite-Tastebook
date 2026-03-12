import json
from typing import List, Dict
from django.conf import settings
from google import genai
from google.genai import types

# Import the abstract base class from our domain layer
from recipe_manager.domain.image_analyzer_interface import ImageAnalyzerInterface


class GeminiImageAnalyzer(ImageAnalyzerInterface):
    """
    Concrete implementation of ImageAnalyzerInterface using Google's Gemini API.
    """

    def __init__(self):
        # Initialize the GenAI client using the API key from Django settings
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Using the recommended model for complex reasoning and multimodal tasks
        self.model_id = "gemini-2.5-flash"

    def analyze_image(self, image_bytes: bytes, ingredients_list: List[str]) -> Dict[str, List[str]]:
        schema = {
            "type": "OBJECT",
            "properties": {
                "matched_ingredients": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                }
            },
            "required": ["matched_ingredients"]
        }

        system_instruction = (
            "You are an expert culinary AI. Analyze the provided image of food items or groceries "
            "and identify which of the following ingredients are present. "
            f"Ingredient list: {json.dumps(ingredients_list)}. "
            "Return ONLY the exact string matches from this list. "
            "Do not add any ingredients not in the list, and do not change the spelling. "
            "Your entire response must be a valid JSON matching the requested schema."
        )

        # Configure the request to enforce the JSON schema and eliminate randomness
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.0
        )

        try:
            # Send the request to Gemini API
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    "Analyze this image and list the matching ingredients."
                ],
                config=config
            )

            # The SDK and schema guarantee the response is a valid JSON string
            return json.loads(response.text)

        except Exception as e:
            raise RuntimeError(f"Gemini API analysis failed: {str(e)}")