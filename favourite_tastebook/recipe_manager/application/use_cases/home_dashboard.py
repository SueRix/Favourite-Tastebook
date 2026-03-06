from recipe_manager.infrastructure.selectors.ingredients import IngredientSelector
from recipe_manager.infrastructure.orm.recipe_search import RecipeSearchORM
from recipe_manager.infrastructure.presentation.featured_recipe import FeaturedRecipePresenter
from recipe_manager.models import SavedRecipe


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
    def _build_ingredients_context(cls, ingredients_queryset, filters):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        return {
            "ingredients": ingredients_queryset,
            # Added selected_ingredients for the unified HTMX partial
            "selected_ingredients": selected,
            "selected_ids": selected_ids,
            "selected_count": len(selected_ids),
        }

    @classmethod
    def build_ingredients_partial(cls, filters):
        qs = IngredientSelector.list_ingredients(filters)
        return cls._build_ingredients_context(qs, filters)

    @classmethod
    def build_search_results_partial(cls, filters):
        query = filters.get("q", "")
        category = filters.get("category")

        qs = IngredientSelector.search_by_name(query, category=category)

        return cls._build_ingredients_context(qs, filters)

    @classmethod
    def build_selected_partial(cls, filters):
        selected = IngredientSelector.list_selected(filters)
        return {
            "selected_ingredients": selected,
        }

    @classmethod
    def build_recipes_partial(cls, filters, user):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        recipes = RecipeSearchORM.find_recipes(filters)
        saved_recipe_ids = set()

        if user.is_authenticated:
            saved_recipe_ids = set(
                SavedRecipe.objects.filter(user=user).values_list('recipe_id', flat=True)
            )

        featured, tier_1, tier_2 = FeaturedRecipePresenter.select(
            recipes,
            recipe_id=filters.get("recipe"),
            selected_ids=selected_ids,
            saved_ids=saved_recipe_ids
        )

        return {
            "selected_count": len(selected_ids),
            "featured": featured,
            "tier_1_recipes": tier_1,
            "tier_2_recipes": tier_2,
        }