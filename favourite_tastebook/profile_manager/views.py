from django.views import View
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from .handlers.profile import profile_detail, profile_edit


@method_decorator(login_required, name="dispatch")
class ProfileDetailView(View):
    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return profile_detail(self.request)


@method_decorator(login_required, name="dispatch")
class ProfileUpdateView(View):
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return profile_edit(request)