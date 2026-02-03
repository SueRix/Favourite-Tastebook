from .mixins import SearchParamsMixin
from .models import Ingredient, Recipe
from recipe_manager.application.use_cases.dashboard import DashboardUseCase
from django.views.generic import ListView, View, TemplateView
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from recipe_manager.application.use_cases.saved_recipes import SavedRecipesUseCase
from recipe_manager.decorators import handle_recipe_exceptions


class MainTastebookView(SearchParamsMixin, TemplateView):
    template_name = "main/recipe_manager.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardUseCase.build_home(self.filters))
        return ctx


class IngredientsPartialView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "partials/ingredients_list.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        data = DashboardUseCase.build_ingredients_partial(self.filters)
        return data["ingredients"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardUseCase.build_ingredients_partial(self.filters))
        return ctx


class IngredientSearchView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "partials/ingredients_list.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        data = DashboardUseCase.build_search_results_partial(self.filters)
        return data["ingredients"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardUseCase.build_search_results_partial(self.filters))
        return ctx


class SelectedIngredientsPartialView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "partials/selected_ingredients.html"
    context_object_name = "selected_ingredients"

    def get_queryset(self):
        data = DashboardUseCase.build_selected_partial(self.filters)
        return data["selected_ingredients"]


class RecipesPartialView(SearchParamsMixin, ListView):
    model = Recipe
    template_name = "partials/recipes_found.html"
    context_object_name = "more_recipes"

    def get_queryset(self):
        data = DashboardUseCase.build_recipes_partial(self.filters)
        return data["more_recipes"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardUseCase.build_recipes_partial(self.filters))
        return ctx


class SavedRecipeListView(LoginRequiredMixin, ListView):
    template_name = 'main/recipe_saved.html'
    context_object_name = 'saved_recipes'

    # ListView требует get_queryset, но мы берем данные из UseCase
    def get_queryset(self):
        data = SavedRecipesUseCase.build_saved_list(self.request.user)
        return data["saved_recipes"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # ctx.update(SavedRecipesUseCase.build_saved_list(self.request.user))
        return ctx


@method_decorator(csrf_exempt, name='dispatch')
class SavedRecipeActionView(LoginRequiredMixin, View):

    @handle_recipe_exceptions
    def post(self, request, recipe_id):
        SavedRecipesUseCase.add_to_saved(request.user, recipe_id)
        return JsonResponse({"detail": "Saved successfully."}, status=201)

    @handle_recipe_exceptions
    def delete(self, request, recipe_id):
        SavedRecipesUseCase.remove_from_saved(request.user, recipe_id)

        if request.headers.get('HX-Request'):
            return HttpResponse(status=200)

        return JsonResponse({"detail": "Removed from saved."}, status=200)
