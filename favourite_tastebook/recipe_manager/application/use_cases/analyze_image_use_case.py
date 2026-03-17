import base64
from typing import Dict
from recipe_manager.infrastructure.ai_adapters.gemini_adapter import GeminiImageAnalyzer

from recipe_manager.infrastructure.repositories.fixture_repository import IngredientFixtureRepository


class AnalyzeImageIngredientsUseCase:
    """
    Application layer: Orchestrates the image analysis logic.
    Delegates data fetching to repositories and AI calls to adapters.
    """

    @classmethod
    def execute(cls, image_base64: str) -> Dict:
        try:
            image_bytes = base64.b64decode(image_base64)
        except Exception as e:
            raise ValueError(f"Failed to decode image: {str(e)}")

        backend_ingredients = IngredientFixtureRepository.get_all_ingredient_names()

        analyzer = GeminiImageAnalyzer()

        raw_result = analyzer.analyze_image(
            image_bytes=image_bytes,
            ingredients_list=backend_ingredients
        )

        matched_items = raw_result.get("matched_ingredients", [])

        return {
            "status": "success",
            "matched_ingredients": matched_items,
            "match_count": len(matched_items)
        }