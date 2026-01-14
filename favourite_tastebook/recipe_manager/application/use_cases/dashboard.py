from recipe_manager.infrastructure.selectors.ingredients import IngredientSelector
from recipe_manager.infrastructure.orm.recipe_search import RecipeSearchORM
from recipe_manager.infrastructure.presentation.featured_recipe import FeaturedRecipePresenter

class DashboardUseCase:
    """
    Application layer: orchestrates scenario for Home/HTMX.
    """

    @classmethod
    def build_home(cls, filters):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        return {
            "categories": IngredientSelector.list_categories(),
            "ingredients": IngredientSelector.list_ingredients(filters),
            "selected_ingredients": selected,
            "selected_ids": selected_ids,
            "selected_count": len(selected_ids),
            "recipes": RecipeSearchORM.find_recipes(filters),
        }

    @classmethod
    def build_ingredients_partial(cls, filters):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        return {
            "ingredients": IngredientSelector.list_ingredients(filters),
            "selected_ids": selected_ids,
            "selected_count": len(selected_ids),
        }

    @classmethod
    def build_selected_partial(cls, filters):
        selected = IngredientSelector.list_selected(filters)
        return {
            "selected_ingredients": selected,
        }

    @classmethod
    def build_recipes_partial(cls, filters):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        recipes = RecipeSearchORM.find_recipes(filters)
        featured, more_recipes = FeaturedRecipePresenter.select(
            recipes,
            recipe_id=filters.get("recipe"),
            selected_ids=selected_ids,
        )

        return {
            "selected_count": len(selected_ids),
            "featured": featured,
            "more_recipes": more_recipes,
        }
