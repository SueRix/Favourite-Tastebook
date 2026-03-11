from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..mixins import SearchParamsMixin
from recipe_manager.application.use_cases.home_dashboard import DashboardUseCase

class MainTastebookView(SearchParamsMixin, TemplateView):
    template_name = "main/recipe_manager.html"

    def get_context_data(self, **kwargs):
        # Retrieve dashboard data using the SearchParamsMixin filters
        ctx = super().get_context_data(**kwargs)
        ctx.update(DashboardUseCase.build_home(self.filters))
        return ctx

class TastesView(LoginRequiredMixin, TemplateView):
    template_name = "profile/tastes_stub.html"