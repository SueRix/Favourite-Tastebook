from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

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
        response = JsonResponse({"status": "success"})
        response["HX-Trigger"] = "tastesUpdated"  # fire event to client
        return response

class RatedTastesPartialView(LoginRequiredMixin, TemplateView):
    template_name = "partials/tastes_rated_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # get fresh data for the rated column
        context.update(TasteManagementUseCase.build_tastes_profile(self.request.user))
        return context

class SearchTastesPartialView(LoginRequiredMixin, TemplateView):
    template_name = "partials/tastes_search_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # get fresh data for the search/unrated column
        context.update(TasteManagementUseCase.build_tastes_profile(self.request.user))
        return context


class ToggleGlobalTasteApiView(LoginRequiredMixin, View):
    @staticmethod
    def post(request, *args, **kwargs):
        raw_val = request.POST.get('disable_taste', 'false')
        is_disabled = str(raw_val).lower() == 'true'

        request.session['disable_taste_logic'] = is_disabled
        request.session.modified = True

        return JsonResponse({
            "status": "success",
            "use_taste_logic": is_disabled
        })