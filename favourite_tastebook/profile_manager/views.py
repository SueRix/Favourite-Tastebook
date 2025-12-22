from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import DetailView, View, TemplateView

from .forms import ProfileForm, UserUpdateForm
from .models import Profile


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = Profile
    template_name = "profile/detail.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile


class ProfileUpdateView(LoginRequiredMixin, View):
    template_name = "profile/edit.html"

    def get_forms(self, user):
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)

        if self.request.method == "POST":
            user_form = UserUpdateForm(self.request.POST, instance=user)
            profile_form = ProfileForm(self.request.POST, self.request.FILES, instance=profile)
        else:
            user_form = UserUpdateForm(instance=user)
            profile_form = ProfileForm(instance=profile)

        return user_form, profile_form

    def get(self, request, *args, **kwargs):
        user_form, profile_form = self.get_forms(request.user)
        ctx = {"user_form": user_form, "profile_form": profile_form}
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        user_form, profile_form = self.get_forms(request.user)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            ctx = {
                "user_form": user_form,
                "profile_form": profile_form,
                "saved": True
            }
            return render(request, self.template_name, ctx)

        ctx = {
            "user_form": user_form,
            "profile_form": profile_form,
            "errors": {
                "user": user_form.errors,
                "profile": profile_form.errors
            },
        }
        return render(request, self.template_name, ctx, status=400)


class TastesView(LoginRequiredMixin, TemplateView):
    template_name = "profile/tastes_stub.html"


class CookbooksView(LoginRequiredMixin, TemplateView):
    template_name = "profile/cookbooks_stub.html"


class SavedRecipesView(LoginRequiredMixin, TemplateView):
    template_name = "profile/saved_stub.html"