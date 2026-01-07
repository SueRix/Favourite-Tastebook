from django.views.generic import ListView, TemplateView
from .mixins import SearchParamsMixin
from .models import Ingredient, Recipe
from .services.search_recipes import RecipeSearchService
from .selectors.ingredients import IngredientSelector


class MainTastebookView(SearchParamsMixin, TemplateView):
    template_name = "recipe_manager.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = IngredientSelector.list_categories()
        ctx["ingredients"] = IngredientSelector.list_ingredients(self.filters)
        ctx["selected_ingredients"] = IngredientSelector.list_selected(self.filters)
        ctx["recipes"] = RecipeSearchService.find_recipes(self.filters)
        return ctx


class RecipesPartialView(SearchParamsMixin, ListView):
    model = Recipe
    template_name = "recipes_found.html"
    context_object_name = "recipes"

    def get_queryset(self):
        return RecipeSearchService.find_recipes(self.filters)


class IngredientsPartialView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "ingredients_list.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        return IngredientSelector.list_ingredients(self.filters)


class SelectedIngredientsPartialView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "selected_ingredients.html"
    context_object_name = "selected_ingredients"

    def get_queryset(self):
        return IngredientSelector.list_selected(self.filters)
