from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, View, UpdateView, detail

from .forms import ProfileForm, UserUpdateForm
from .models import Profile

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

class ProfileUpdateView(OwnerRequiredMixin, LoginRequiredMixin, View):
    template_name = "profile/edit.html"

    def get(self, request, username):
        user = request.user
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=user.profile)
        return render(request, self.template_name, {
            "user_form": user_form,
            "profile_form": profile_form,
        })

    def post(self, request, username):
        user = request.user
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
        else:
            messages.error(request, "Please correct the error below.")
        return render(request, self.template_name, {
            "user_form": user_form,
            "profile_form": profile_form,
        })

