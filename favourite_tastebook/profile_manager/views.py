from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, View

from .exceptions import ProfileNotFound, InvalidFormData
from .forms import ProfileForm, UserUpdateForm
from .models import Profile
from django.views.generic import TemplateView


class ProfileDetailView(DetailView):
    model = Profile
    template_name = "profile/detail.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        username = self.kwargs.get("username")
        user = get_object_or_404(User, username=username)
        profile, _ = Profile.objects.get_or_create(user=user)
        return profile


class OwnerRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        username = self.kwargs.get("username")
        return self.request.user.is_authenticated and self.request.user.username == username

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise Http404("You cannot edit another user's profile.")
        return super().handle_no_permission()


class ProfileUpdateView(LoginRequiredMixin, OwnerRequiredMixin, View):
    template_name = "profile/edit.html"

    def _get_forms(self, request):
        try:
            profile = request.user.profile
        except Profile.DoesNotExist as exc:
            raise ProfileNotFound("Profile object not found for current user.") from exc

        if request.method == "POST":
            user_form = UserUpdateForm(request.POST, instance=request.user)
            profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        else:
            user_form = UserUpdateForm(instance=request.user)
            profile_form = ProfileForm(instance=profile)
        return user_form, profile_form

    def get(self, request, username):
        try:
            user_form, profile_form = self._get_forms(request)
        except ProfileNotFound:
            raise Http404("Profile not found.")
        ctx = {"user_form": user_form, "profile_form": profile_form}
        return render(request, self.template_name, ctx, status=200)

    def post(self, request, username):
        try:
            user_form, profile_form = self._get_forms(request)
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                ctx = {"user_form": UserUpdateForm(instance=request.user),
                       "profile_form": ProfileForm(instance=request.user.profile),
                       "saved": True}
                return render(request, self.template_name, ctx, status=200)

            raise InvalidFormData(user_errors=user_form.errors, profile_errors=profile_form.errors)

        except InvalidFormData as e:
            ctx = {
                "user_form": user_form,
                "profile_form": profile_form,
                "errors": {"user": e.user_errors, "profile": e.profile_errors},
            }
            return render(request, self.template_name, ctx, status=400)

        except ProfileNotFound:
            raise Http404("Profile not found.")

class TastesView(TemplateView):
    template_name = "profiles/tastes_stub.html"

class CookbooksView(TemplateView):
    template_name = "profiles/cookbooks_stub.html"

class SavedRecipesView(TemplateView):
    template_name = "profiles/saved_stub.html"
