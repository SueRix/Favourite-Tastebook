from django.views import View
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from .handlers.profile import profile_detail, profile_edit


@method_decorator(login_required, name="dispatch")
class ProfileDetailView(View):
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return profile_detail(request)


@method_decorator(login_required, name="dispatch")
class ProfileUpdateView(View):
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return profile_edit(request)



class TastesView(LoginRequiredMixin, TemplateView):
    template_name = "profile/tastes_stub.html"


class CookbooksView(LoginRequiredMixin, TemplateView):
    template_name = "profile/cookbooks_stub.html"


class SavedRecipesView(LoginRequiredMixin, TemplateView):
    template_name = "profile/saved_stub.html"
