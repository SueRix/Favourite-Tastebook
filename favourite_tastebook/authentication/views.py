from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect
from django.views.generic import TemplateView

from .forms import ProfileForm, AccountForm, PasswordUpdateForm
from .models import Profile

class RegisterView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('home')

class UpdateProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'update_profile.html'

    def _get_profile(self):
        obj, _ = Profile.objects.get_or_create(user=self.request.user)
        return obj

    # ---------- GET ----------
    def get(self, request, *args, **kwargs):
        profile = self._get_profile()
        context = {
            "profile_form": ProfileForm(instance=profile),
            "account_form": AccountForm(instance=request.user),
            "password_form": PasswordUpdateForm(user=request.user),
        }
        return self.render_to_response(context)

    # ---------- POST ----------
    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        if action == "profile":
            profile = self._get_profile()
            form = ProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated.")
            else:
                messages.error(request, "Fix errors in the profile section.")
            return redirect("update_profile")

        if action == "account":
            form = AccountForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Account details updated.")
            else:
                messages.error(request, "Fix errors in username/email.")
            return redirect("update_profile")

        if action == "password":
            form = PasswordUpdateForm(user=request.user, data=request.POST)
            if form.is_valid():
                user = form.save()                     # saves the new password
                update_session_auth_hash(request, user) # keep the user logged in
                messages.success(request, "Password changed.")
            else:
                messages.error(request, "Fix errors in the password section.")
            return redirect("update_profile")

        messages.error(request, "Unknown action.")
        return redirect("update_profile")
