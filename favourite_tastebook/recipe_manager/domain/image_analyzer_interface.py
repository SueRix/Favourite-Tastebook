from abc import ABC, abstractmethod
from typing import List, Dict


class ImageAnalyzerInterface(ABC):
    """
    Abstract interface for image analysis services.
    Enforces the contract for any AI vendor we might use now or in the future.
    """

    @abstractmethod
    def analyze_image(self, image_bytes: bytes, ingredients_list: List[str]) -> Dict[str, List[str]]:
        """
        Analyzes an image and finds matches against a provided list of ingredients.

        Args:
            image_bytes (bytes): The raw image data.
            ingredients_list (List[str]): A list of possible ingredients to look for.

        Returns:
            Dict[str, List[str]]: A dictionary containing exactly one key 'matched_ingredients'
                                  which maps to a list of strings found in the image.
        """
        pass