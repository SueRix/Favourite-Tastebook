from typing import Any

from django.db.models import QuerySet
from django.http import HttpRequest
from django.views.generic import TemplateView, ListView
from django.utils.functional import cached_property

from . import selectors
from .models import Ingredient, Recipe


class TastebookRequestMixin:
    """
    Parses and caches common request parameters.
    """
    request: HttpRequest

    @cached_property
    def selected_ids(self) -> list[int]:
        return selectors.extract_ingredient_ids(self.request.GET)

    @cached_property
    def strict_required(self) -> bool:
        return self._parse_bool("strict")

    @cached_property
    def use_tastes(self) -> bool:
        return self._parse_bool("use_tastes")

    @property
    def search_query(self) -> str:
        return self.request.GET.get("q", "").strip()

    @property
    def category_filter(self) -> str:
        return self.request.GET.get("category", "").strip()

    def _parse_bool(self, key: str) -> bool:
        return self.request.GET.get(key) in ("1", "true", "yes", "on")


class MainTastebookView(TastebookRequestMixin, TemplateView):
    """Entry point: renders full page with initial state (SSR)."""
    template_name = "main/recipe_manager.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)

        # Filters state
        ctx["q"] = self.search_query
        ctx["category"] = self.category_filter
        ctx["categories"] = selectors.get_ingredient_categories()
        ctx["strict"] = self.strict_required
        ctx["use_tastes"] = self.use_tastes

        # Basket state
        ctx["selected_ids"] = self.selected_ids
        ctx["selected_ingredients"] = (
            Ingredient.objects
            .filter(id__in=self.selected_ids)
            .order_by("category", "name")
        )

        # Available ingredients
        ctx["ingredients"] = selectors.get_ingredients(
            q=self.search_query,
            category=self.category_filter
        )

        # Search results (lazy evaluation)
        if self.selected_ids:
            ctx["recipes"] = selectors.search_recipes_by_ingredients(
                selected_ids=self.selected_ids,
                strict_required=self.strict_required,
            )
        else:
            ctx["recipes"] = Recipe.objects.none()

        return ctx


class IngredientsPartialView(TastebookRequestMixin, ListView):
    """HTMX partial: updates available ingredients list."""
    model = Ingredient
    template_name = "partials/ingredients_list.html"
    context_object_name = "ingredients"
    paginate_by = 50

    def get_queryset(self) -> QuerySet:
        return selectors.get_ingredients(
            q=self.search_query,
            category=self.category_filter,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["selected_ids"] = set(self.selected_ids)
        ctx["q"] = self.search_query
        ctx["category"] = self.category_filter
        ctx["categories"] = selectors.get_ingredient_categories()
        return ctx


class SelectedIngredientsPartialView(TastebookRequestMixin, ListView):
    """HTMX partial: updates the 'basket'."""
    model = Ingredient
    template_name = "partials/selected_ingredients.html"
    context_object_name = "selected_ingredients"

    def get_queryset(self) -> QuerySet:
        if not self.selected_ids:
            return Ingredient.objects.none()

        return (
            Ingredient.objects
            .filter(id__in=self.selected_ids)
            .order_by("category", "name")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["selected_ids"] = self.selected_ids
        return ctx


class RecipesPartialView(TastebookRequestMixin, ListView):
    """HTMX partial: recalculates recipes based on current selection."""
    model = Recipe
    template_name = "partials/recipes_found.html"
    context_object_name = "recipes"
    paginate_by = 20

    def get_queryset(self) -> QuerySet:
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