from django.views.generic import ListView, TemplateView

from . import selectors
from .models import Ingredient, Recipe
from .mixins import SearchFormMixin


class MainTastebookView(SearchFormMixin, TemplateView):
    template_name = "recipe_manager.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        if self.search_form.is_valid():
            data = self.search_form.cleaned_data

            # FIX: form field name is "ingredient", not "selected_ids"
            selected_qs = data.get("ingredient")

            recipes = Recipe.objects.none()
            selected_ingredients = Ingredient.objects.none()

            if selected_qs:
                selected_ingredients = selected_qs.order_by("name")
                selected_ids_list = list(selected_qs.values_list("id", flat=True))

                recipes = selectors.search_recipes_by_ingredients(
                    selected_ids=selected_ids_list,
                    strict_required=data.get("strict", False),
                )

            ctx.update(
                {
                    "categories": selectors.get_ingredient_categories(),
                    "ingredients": selectors.get_ingredients(
                        q=data.get("q"),
                        category=data.get("category"),
                    ),
                    "selected_ingredients": selected_ingredients,
                    "recipes": recipes,
                }
            )

        return ctx


class IngredientsPartialView(SearchFormMixin, ListView):
    model = Ingredient
    template_name = "ingredients_list.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        if not self.search_form.is_valid():
            return Ingredient.objects.none()

        data = self.search_form.cleaned_data
        return selectors.get_ingredients(
            q=data.get("q"),
            category=data.get("category"),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.search_form.is_valid():
            data = self.search_form.cleaned_data
            ctx.update(
                {
                    "q": data.get("q"),
                    "category": data.get("category"),
                    "categories": selectors.get_ingredient_categories(),
                }
            )
        return ctx


class SelectedIngredientsPartialView(SearchFormMixin, ListView):
    model = Ingredient
    template_name = "selected_ingredients.html"
    context_object_name = "selected_ingredients"

    def get_queryset(self):
        if not self.search_form.is_valid():
            return Ingredient.objects.none()

        # FIX: form field name is "ingredient"
        qs = self.search_form.cleaned_data.get("ingredient")
        if qs:
            return qs.order_by("name")

        return Ingredient.objects.none()


class RecipesPartialView(SearchFormMixin, ListView):
    model = Recipe
    template_name = "recipes_found.html"
    context_object_name = "recipes"

    def get_queryset(self):
        if not self.search_form.is_valid():
            return Recipe.objects.none()

        # FIX: form field name is "ingredient"
        selected_qs = self.search_form.cleaned_data.get("ingredient")
        if not selected_qs:
            return Recipe.objects.none()

        selected_ids_list = list(selected_qs.values_list("id", flat=True))

        return selectors.search_recipes_by_ingredients(
            selected_ids=selected_ids_list,
            strict_required=self.search_form.cleaned_data.get("strict", False),
        )