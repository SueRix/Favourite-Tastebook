from django.conf import settings
from recipe_manager.domain.enums import Importance
from recipe_manager.domain.parsers.recipe_steps import RecipeStepsParser


class FeaturedRecipePresenter:
    @staticmethod
    def _get_poster_url(recipe):
        if recipe.image_url:
            return recipe.image_url.url

        if recipe.cuisine:
            cuisine_slug = recipe.cuisine.name.lower()
        else:
            cuisine_slug = "general"

        return f"{settings.MEDIA_URL}recipes/cuisine/{cuisine_slug}/{recipe.id}.jpg"

    @classmethod
    def select(cls, recipes, recipe_id=None, selected_ids=None, saved_ids=None):
        if not recipes.exists():
            return None, [], []

        featured = None

        if recipe_id:
            featured = recipes.filter(id=recipe_id).first()
        else:
            first_recipe = recipes.first()
            # Auto-expand only if it's a Tier 1 match
            if getattr(first_recipe, 'relevance_tier', 3) == 1:
                featured = first_recipe

        if featured:
            featured.poster_url = cls._get_poster_url(featured)
            featured.steps = RecipeStepsParser.parse(featured.description)
            featured.cuisine_label = featured.cuisine.name if featured.cuisine_id else "General"

            saved_ids = saved_ids or set()
            featured.is_saved = featured.id in saved_ids

            selected_set = set(int(x) for x in (selected_ids or []))
            recipe_items = list(featured.ingredients.all())

            def build_item(ri):
                ing = ri.ingredient
                return {
                    "id": ing.id,
                    "name": ing.name,
                    "category": getattr(ing, "category", None),
                    "amount": ri.amount,
                    "unit": ri.unit,
                    "importance": ri.importance,
                    "is_selected": ing.id in selected_set,
                }

            def build_group(title: str, importance: str):
                items = [build_item(ri) for ri in recipe_items if ri.importance == importance]
                return {"title": title, "items": items}

            featured.ingredient_groups = [
                build_group("Required", Importance.REQUIRED),
                build_group("Secondary", Importance.SECONDARY),
                build_group("Optional", Importance.OPTIONAL),
            ]

            featured.ingredients_detailed = [build_item(ri) for ri in recipe_items]
            featured.matched_count = getattr(featured, 'total_matches',
                                             sum(1 for ri in recipe_items if ri.ingredient_id in selected_set))
            featured.missing_count = getattr(featured, 'missing_required', 0) + getattr(featured, 'missing_secondary',
                                                                                        0)

        # Group remaining recipes
        more = recipes.exclude(id=featured.id) if featured else recipes

        tier_1 = [r for r in more if getattr(r, 'relevance_tier', 3) == 1]
        tier_2 = [r for r in more if getattr(r, 'relevance_tier', 3) == 2]

        return featured, tier_1, tier_2