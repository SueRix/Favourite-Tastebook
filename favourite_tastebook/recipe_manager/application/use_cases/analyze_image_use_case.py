import base64

from typing import List, Dict
from recipe_manager.infrastructure.ai_adapters.gemini_adapter import GeminiImageAnalyzer


class AnalyzeImageIngredientsUseCase:
    """
    Application layer: Orchestrates the fridge analysis logic.
    Hides the AI adapter initialization and data transformation from the View/Task layers.
    """

    @classmethod
    def execute(cls, image_base64: str, user_ingredients: List[str]) -> Dict:
        """
        Executes the business logic for analyzing an image against a list of ingredients.

        Args:
            image_base64 (str): The uploaded image, encoded in base64.
            user_ingredients (List[str]): The list of ingredient names from the user.

        Returns:
            Dict: A formatted dictionary with the analysis results and metadata.
        """
        try:
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            raise ValueError(f"Failed to decode image: {str(e)}")

        analyzer = GeminiImageAnalyzer()

        raw_result = analyzer.analyze_image(
            image_bytes=image_bytes,
            ingredients_list=user_ingredients
        )

        matched_items = raw_result.get("matched_ingredients", [])

        return {
            "status": "success",
            "matched_ingredients": matched_items,
            "match_count": len(matched_items)
        }
