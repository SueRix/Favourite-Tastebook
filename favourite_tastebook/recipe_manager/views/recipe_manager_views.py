from django.views.generic import ListView, TemplateView
from ..mixins import SearchParamsMixin
from ..models import Ingredient
from recipe_manager.application.use_cases.home_dashboard import DashboardUseCase


class IngredientsPartialView(SearchParamsMixin, ListView):
    model = Ingredient
    template_name = "partials/ingredients_panel.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        data = DashboardUseCase.build_ingredients_partial(self.filters)
        return data["ingredients"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardUseCase.build_ingredients_partial(self.filters))
        return ctx


class RecipesPartialView(SearchParamsMixin, TemplateView):
    template_name = "partials/recipes_found.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        new_context = DashboardUseCase.build_recipes_partial(
            self.filters,
            self.request.user
        )
        ctx.update(new_context)
        return ctx
