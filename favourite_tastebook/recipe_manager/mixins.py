from django.utils.functional import cached_property
from django.views.generic.base import ContextMixin
from django.http import HttpRequest
from .forms import RecipeSearchForm


class SearchFormMixin(ContextMixin):
    """
    A mixin for initializing the search form.
    Responsible for creating the form and passing basic variables into the context.
    """
    request: HttpRequest
    @cached_property
    def search_form(self):
        return RecipeSearchForm(self.request.GET)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = self.search_form

        if self.search_form.is_valid():
            ctx["selected_ids"] = self.search_form.cleaned_data.get("ingredient")
            ctx["strict"] = self.search_form.cleaned_data.get('strict', False)

        return ctx