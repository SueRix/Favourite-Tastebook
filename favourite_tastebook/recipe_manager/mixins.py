from django.http import HttpRequest
from django.utils.functional import cached_property
from django.views.generic.base import ContextMixin
from .forms import RecipeSearchForm

class SearchParamsMixin(ContextMixin):

    request: HttpRequest
    @cached_property
    def search_form(self):
        return RecipeSearchForm(self.request.GET)

    @property
    def filters(self):
        if self.search_form.is_valid():
            return self.search_form.cleaned_data
        return {}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = self.search_form
        ctx.update(self.filters)
        return ctx