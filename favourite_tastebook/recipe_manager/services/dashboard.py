from recipe_manager.models import Ingredient, Recipe
from recipe_manager.selectors.ingredients import IngredientSelector
from recipe_manager.services.search_recipes import RecipeSearchService


class DashboardService:
    @classmethod
    def get_main_context(cls, cleaned_data):
        """
        Собирает полный контекст для главной страницы.
        Вьюха просто отдает словарь cleaned_data и получает готовый ответ.
        """
        selected_qs = cleaned_data.get("ingredient")
        strict = cleaned_data.get("strict", False)

        recipes = Recipe.objects.none()
        selected_ingredients = Ingredient.objects.none()

        if selected_qs:
            selected_ingredients = selected_qs.order_by("name")
            recipes = RecipeSearchService.find_by_ingredients(selected_qs, strict)

        return {
            "categories": IngredientSelector.get_categories(),
            "ingredients": IngredientSelector.get_list(
                q=cleaned_data.get("q"),
                category=cleaned_data.get("category")
            ),
            "selected_ingredients": selected_ingredients,
            "recipes": recipes,
        }