from typing import Any

from django.utils.functional import cached_property
from django.views.generic import ListView, TemplateView

from . import selectors
from .models import Ingredient, Recipe
from .http.parsers.recipe_search_params import RecipeSearchFilters


class TastebookRequestMixin:
    """
    Acts as a bridge between the View and the clean Data Object.
    Extracts data using RecipeSearchFilters and exposes properties
    for convenient usage in views.
    """
    request: Any

    @cached_property
    def search_filters(self) -> RecipeSearchFilters:
        return RecipeSearchFilters.from_request(self.request)

    def __getattr__(self, name: str):
        if name in {"q", "category", "strict_required", "selected_ids"}:
            return getattr(self.search_filters, name)
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    @cached_property
    def selected_ingredients_qs(self):
        if not self.selected_ids:
            return Ingredient.objects.none()
        return Ingredient.objects.filter(id__in=self.selected_ids).order_by("name")


class MainTastebookView(TastebookRequestMixin, TemplateView):
    """Full SSR search page."""
    template_name = "recipe_manager.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        ctx["q"] = self.q
        ctx["category"] = self.category
        ctx["strict"] = self.strict_required
        ctx["selected_ids"] = self.selected_ids

        ctx["categories"] = selectors.get_ingredient_categories()
        ctx["ingredients"] = selectors.get_ingredients(q=self.q, category=self.category)
        ctx["selected_ingredients"] = self.selected_ingredients_qs

        ctx["recipes"] = (
            selectors.search_recipes_by_ingredients(
                selected_ids=self.selected_ids,
                strict_required=self.strict_required,
            )
            if self.selected_ids
            else Recipe.objects.none()
        )

        return ctx


class IngredientsPartialView(TastebookRequestMixin, ListView):
    """HTMX partial: ingredient list (search/category)."""
    model = Ingredient
    template_name = "ingredients_list.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        return selectors.get_ingredients(q=self.q, category=self.category)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.q
        ctx["category"] = self.category
        ctx["categories"] = selectors.get_ingredient_categories()
        ctx["selected_ids"] = self.selected_ids
        return ctx


class SelectedIngredientsPartialView(TastebookRequestMixin, ListView):
    """HTMX partial: selected ingredients."""
    model = Ingredient
    template_name = "selected_ingredients.html"
    context_object_name = "selected_ingredients"

    def get_queryset(self):
        return self.selected_ingredients_qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["selected_ids"] = self.selected_ids
        return ctx


class RecipesPartialView(TastebookRequestMixin, ListView):
    """HTMX partial: recipes for the current selection."""
    model = Recipe
    template_name = "recipes_found.html"
    context_object_name = "recipes"

    def get_queryset(self):
        if not self.selected_ids:
            return Recipe.objects.none()

        return selectors.search_recipes_by_ingredients(
            selected_ids=self.selected_ids,
            strict_required=self.strict_required,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["strict"] = self.strict_required
        ctx["selected_ids"] = self.selected_ids
        return ctx
