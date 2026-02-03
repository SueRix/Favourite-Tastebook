from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from recipe_saver.crud import recipe_saver_crud as crud
from .decorators import handle_recipe_exceptions
from .presentation import SavedRecipePresenter


class SavedRecipeListView(LoginRequiredMixin, View):
    def get(self, request):
        queryset = crud.get_user_saved_recipes(self.request.user)
        data = SavedRecipePresenter(queryset).data()
        return JsonResponse(data, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class SavedRecipeActionView(LoginRequiredMixin, View):

    @handle_recipe_exceptions
    def post(self, request, recipe_id):
        crud.add_recipe_to_saved(self.request.user, recipe_id)
        return JsonResponse({"detail": "Recipe successfully saved."}, status=201)

    @handle_recipe_exceptions
    def delete(self, request, recipe_id):
        crud.remove_recipe_from_saved(self.request.user, recipe_id)
        return JsonResponse({"detail": "Recipe removed from saved."}, status=200)
