from django.views.generic import ListView, TemplateView

from .mixins import SearchParamsMixin
from .models import Ingredient, Recipe
from .services.dashboard import DashboardService


class MainTastebookView(SearchParamsMixin, TemplateView):
    template_name = "main/recipe_manager.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardService.build_home(self.filters))
        return ctx


class IngredientsPartialView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "partials/ingredients_list.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        data = DashboardService.build_ingredients_partial(self.filters)
        return data["ingredients"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardService.build_ingredients_partial(self.filters))
        return ctx


class SelectedIngredientsPartialView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "partials/selected_ingredients.html"
    context_object_name = "selected_ingredients"

    def get_queryset(self):
        data = DashboardService.build_selected_partial(self.filters)
        return data["selected_ingredients"]


class RecipesPartialView(SearchParamsMixin, ListView):
    model = Recipe
    template_name = "partials/recipes_found.html"
    context_object_name = "recipes"

    def get_queryset(self):
        data = DashboardService.build_recipes_partial(self.filters)
        return data["recipes"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardService.build_recipes_partial(self.filters))
        return ctx





