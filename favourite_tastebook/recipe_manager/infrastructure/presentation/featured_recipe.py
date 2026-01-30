from django.conf import settings
from recipe_manager.domain.enums import Importance
from recipe_manager.domain.parsers.recipe_steps import RecipeStepsParser


class FeaturedRecipePresenter:
    """
    Presentation adapter: Prepares recipe data specifically for display in the UI.
    """

    @staticmethod
    def _get_poster_url(recipe):
        """
            A private method for determining the path to an image.
            The logic is completely dynamic, based on the recipe ID.
        """
        if recipe.image_url:
            return recipe.image_url.url

        if recipe.cuisine:
            cuisine_slug = recipe.cuisine.name.lower()
        else:
            cuisine_slug = "general"

        return f"{settings.MEDIA_URL}recipes/cuisine/{cuisine_slug}/{recipe.id}.jpg"

    @classmethod
    def select(cls, recipes, recipe_id=None, selected_ids=None):

        if not recipes.exists():
            return None, recipes.none()

        featured = recipes.filter(id=recipe_id).first() if recipe_id else recipes.first()

        if not featured:
            return None, recipes.none()

        featured.poster_url = cls._get_poster_url(featured)

        featured.steps = RecipeStepsParser.parse(featured.description)
        featured.cuisine_label = featured.cuisine.name if featured.cuisine_id else "General"

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

        featured.matched_count = sum(1 for ri in recipe_items if ri.ingredient_id in selected_set)
        featured.missing_count = len(recipe_items) - featured.matched_count

        more = recipes.exclude(id=featured.id)

        return featured, more