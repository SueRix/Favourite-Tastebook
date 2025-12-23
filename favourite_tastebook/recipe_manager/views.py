from django.views.generic import TemplateView, ListView
from django.utils.functional import cached_property

from . import selectors
from .models import Ingredient, Recipe


class MainTastebookView(TemplateView):
    template_name = "main/recipe_manager.html"

    @cached_property
    def selected_ids(self) -> list[int]:
        return selectors.parse_selected_ingredient_ids(self.request.GET)

    @cached_property
    def strict_required(self) -> bool:
        return self.request.GET.get("strict") in ("1", "true", "yes", "on")

    @cached_property
    def use_tastes(self) -> bool:
        return self.request.GET.get("use_tastes") in ("1", "true", "yes", "on")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["q"] = self.request.GET.get("q", "")
        ctx["category"] = self.request.GET.get("category", "")
        ctx["categories"] = selectors.get_ingredient_categories()

        # Selected ingredients
        ctx["selected_ids"] = self.selected_ids
        ctx["selected_ingredients"] = (
            Ingredient.objects.filter(id__in=self.selected_ids).order_by("category", "name")
        )

        # Available ingredients
        ctx["ingredients"] = selectors.get_ingredients(q=ctx["q"], category=ctx["category"])

        # Recipes found
        ctx["strict"] = self.strict_required
        ctx["use_tastes"] = self.use_tastes

        if self.selected_ids:
            ctx["recipes"] = selectors.search_recipes_by_ingredients(
                selected_ids=self.selected_ids,
                strict_required=self.strict_required,
            )
        else:
            ctx["recipes"] = Recipe.objects.none()

        return ctx


class IngredientsPartialView(ListView):
    model = Ingredient
    template_name = "partials/ingredients_list.html"
    context_object_name = "ingredients"
    paginate_by = 50

    @cached_property
    def selected_ids(self) -> list[int]:
        return selectors.parse_selected_ingredient_ids(self.request.GET)

    def get_queryset(self):
        return selectors.get_ingredients(
            q=self.request.GET.get("q"),
            category=self.request.GET.get("category"),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["selected_ids"] = set(self.selected_ids)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["category"] = self.request.GET.get("category", "")
        ctx["categories"] = selectors.get_ingredient_categories()
        return ctx


class SelectedIngredientsPartialView(ListView):
    model = Ingredient
    template_name = "partials/selected_ingredients.html"
    context_object_name = "selected_ingredients"

    @cached_property
    def selected_ids(self) -> list[int]:
        return selectors.parse_selected_ingredient_ids(self.request.GET)

    def get_queryset(self):
        if not self.selected_ids:
            return Ingredient.objects.none()
        return Ingredient.objects.filter(id__in=self.selected_ids).order_by("category", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["selected_ids"] = self.selected_ids
        return ctx


class RecipesPartialView(ListView):
    model = Recipe
    template_name = "partials/recipes_found.html"
    context_object_name = "recipes"
    paginate_by = 20

    @cached_property
    def selected_ids(self) -> list[int]:
        return selectors.parse_selected_ingredient_ids(self.request.GET)

    @cached_property
    def strict_required(self) -> bool:
        return self.request.GET.get("strict") in ("1", "true", "yes", "on")

    def get_queryset(self):
        if not self.selected_ids:
            return Recipe.objects.none()

        return selectors.search_recipes_by_ingredients(
            selected_ids=self.selected_ids,
            strict_required=self.strict_required,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["strict"] = self.strict_required
        ctx["selected_ids"] = self.selected_ids
        return ctx
