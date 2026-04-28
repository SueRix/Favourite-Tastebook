from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from recipe_manager.application.use_cases.taste_management import TasteManagementUseCase

class RecipeLikeApiView(LoginRequiredMixin, View):

    @staticmethod
    def post(request, recipe_id, *args, **kwargs):
        TasteManagementUseCase.apply_recipe_like(request.user, recipe_id)
        return JsonResponse({"status": "success", "message": "profile updated"})

class IngredientTasteUpdateApiView(LoginRequiredMixin, View):

    @staticmethod
    def post(request, *args, **kwargs):
        ingredient_id = request.POST.get('ingredient_id')
        score = request.POST.get('score')

        if not ingredient_id or score is None:
            return JsonResponse({"status": "error", "message": "missing data"}, status=400)

        TasteManagementUseCase.update_ingredient_taste(
            request.user,
            int(ingredient_id),
            int(score)
        )
        return JsonResponse({"status": "success"})