import math
from typing import List, Dict


class TasteVectorModel:
    # mathematical core of the recommendation system.
    # implements cosine similarity for taste vectors.

    @staticmethod
    def rank_by_tastes(recipes_data: List[Dict], user_weights: Dict[str, int]) -> List[Dict]:

        user_mag_sq = sum(weight ** 2 for weight in user_weights.values())
        user_magnitude = math.sqrt(user_mag_sq)

        for recipe in recipes_data:
            features = [f"i_{ing_id}" for ing_id in recipe.get('ingredient_ids', [])]
            if recipe.get('cuisine_id'):
                features.append(f"c_{recipe['cuisine_id']}")

            if not features or user_magnitude == 0:
                recipe['taste_score'] = 0
                recipe['total_final_score'] = recipe.get('base_score', 0)
                continue

            dot_product = sum(user_weights.get(feature, 0) for feature in features)
            recipe_magnitude = math.sqrt(len(features))
            cosine_sim = dot_product / (user_magnitude * recipe_magnitude)

            recipe['taste_score'] = cosine_sim
            recipe['total_final_score'] = recipe.get('base_score', 0) + (cosine_sim * 5)

        return sorted(
            recipes_data,
            key=lambda x: (x.get('tier', 3), -x['total_final_score'])
        )