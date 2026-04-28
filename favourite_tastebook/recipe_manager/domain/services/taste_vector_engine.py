import math
from typing import List, Dict


class TasteVectorModel:
    # mathematical core of the recommendation system.
    # implements cosine similarity for taste vectors.

    @staticmethod
    def rank_by_tastes(recipes_data: List[Dict], user_weights: Dict[int, int]) -> List[Dict]:
        # recipes_data: list of dicts with recipe data
        # user_weights: {ingredient_id: weight_value}

        # calculate user vector magnitude
        user_mag_sq = sum(weight ** 2 for weight in user_weights.values())
        user_magnitude = math.sqrt(user_mag_sq)

        for recipe in recipes_data:
            recipe_ingredients = recipe.get('ingredient_ids', [])

            # handle edge cases: no ingredients or empty user preferences
            if not recipe_ingredients or user_magnitude == 0:
                recipe['taste_score'] = 0
                recipe['total_final_score'] = recipe.get('base_score', 0)
                continue

            # calculate dot product
            dot_product = 0
            for ing_id in recipe_ingredients:
                weight = user_weights.get(ing_id, 0)
                dot_product += weight

            # calculate recipe vector magnitude
            # assuming presence of ingredient equals 1, magnitude is sqrt(count)
            recipe_magnitude = math.sqrt(len(recipe_ingredients))

            # cosine similarity calculation
            cosine_sim = dot_product / (user_magnitude * recipe_magnitude)
            recipe['taste_score'] = cosine_sim

            # final score calculation with weight 5 for taste
            recipe['total_final_score'] = recipe.get('base_score', 0) + (cosine_sim * 5)

        # sort by total final score in descending order
        return sorted(
            recipes_data,
            key=lambda x: (x.get('tier', 3), -x['total_final_score'])
        )