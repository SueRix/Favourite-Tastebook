#FIXME: this file as a orchestrator must be extracted to another layer
from recipe_manager.selectors.ingredients import IngredientSelector
from recipe_manager.services.search_recipes import RecipeSearchService
from recipe_manager.services.recipe_steps import RecipeStepsService


class DashboardService:
    """
    Single source of truth for building Home/HTMX contexts from normalized filters.

    Input:
        filters: dict-like (SearchParamsMixin.filters == cleaned_data)

    Output:
        dict suitable for ctx.update(...)
    """

    @classmethod
    def build_home(cls, filters):
        """
        Full context for the main page render (recipe_manager.html).
        """
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        return {
            "categories": IngredientSelector.list_categories(),
            "ingredients": IngredientSelector.list_ingredients(filters),
            "selected_ingredients": selected,
            "selected_ids": selected_ids,
            "selected_count": len(selected_ids),
            "recipes": RecipeSearchService.find_recipes(filters),
        }

    @classmethod
    def build_ingredients_partial(cls, filters):
        """
        Context for ingredients_list.html partial.
        Must include selected_ids/selected_count to keep UI state stable after HTMX swaps.
        """
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        return {
            "ingredients": IngredientSelector.list_ingredients(filters),
            "selected_ids": selected_ids,
            "selected_count": len(selected_ids),
        }

    @classmethod
    def build_selected_partial(cls, filters):
        """
        Context for selected_ingredients.html partial.
        """
        selected = IngredientSelector.list_selected(filters)
        return {
            "selected_ingredients": selected,
        }

    @classmethod

    #ARCH-TODO: logic of recipes validation must be extracted to another low-layer file.
    def build_recipes_partial(cls, filters):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        recipes = RecipeSearchService.find_recipes(filters)

        featured = None
        more_recipes = recipes.none()

        rid = filters.get("recipe")

        if recipes.exists():
            if rid:
                featured = recipes.filter(id=rid).first()

            if featured is None:
                featured = recipes.first()

            featured.steps = RecipeStepsService.split(featured.description)
            more_recipes = recipes.exclude(id=featured.id)

        return {
            "selected_count": len(selected_ids),
            "featured": featured,
            "more_recipes": more_recipes,
        }
