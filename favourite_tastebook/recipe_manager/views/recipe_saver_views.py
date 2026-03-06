from django.views.generic import ListView, View
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from recipe_manager.application.use_cases.saved_recipes_dashboard import SavedRecipesUseCase
from recipe_manager.decorators import handle_recipe_exceptions


class SavedRecipeListView(LoginRequiredMixin, ListView):
    template_name = 'main/recipe_saved.html'
    context_object_name = 'saved_recipes'

    def get_queryset(self):
        # Retrieve the list of saved recipes for the authenticated user
        data = SavedRecipesUseCase.build_saved_list(self.request.user)
        return data["saved_recipes"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(SavedRecipesUseCase.build_saved_list(self.request.user))
        return ctx


class SavedRecipeActionView(LoginRequiredMixin, View):

    @handle_recipe_exceptions
    def post(self, request, recipe_id):
        # Add recipe to user's saved list
        SavedRecipesUseCase.add_to_saved(request.user, recipe_id)
        return JsonResponse({"detail": "Saved successfully."}, status=201)

    @handle_recipe_exceptions
    def delete(self, request, recipe_id):
        # Remove recipe from user's saved list
        SavedRecipesUseCase.remove_from_saved(request.user, recipe_id)

        # Handle HTMX request specific return
        if request.headers.get('HX-Request'):
            return HttpResponse(status=200)

        return JsonResponse({"detail": "Removed from saved."}, status=200)