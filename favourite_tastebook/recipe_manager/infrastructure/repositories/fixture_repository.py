import os
import json
from django.conf import settings
from typing import List


class IngredientFixtureRepository:
    """
    Infrastructure layer: Handles data retrieval from local files.
    """

    @classmethod
    def get_all_ingredient_names(cls) -> List[str]:
        # Construct path to the fixture
        fixture_path = os.path.join(
            settings.BASE_DIR,
            'recipe_manager', 'fixtures', 'ingredients', '01_ing.json'
        )

        try:
            with open(fixture_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            names_list = []
            for item in data:
                if isinstance(item, dict) and "fields" in item and "name" in item["fields"]:
                    names_list.append(item["fields"]["name"])
                elif isinstance(item, dict) and "name" in item:
                    names_list.append(item["name"])
                elif isinstance(item, str):
                    names_list.append(item)

            return names_list
        except Exception as e:
            raise RuntimeError(f"Failed to load ingredients fixture: {str(e)}")