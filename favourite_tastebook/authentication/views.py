from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib import messages
from .forms import ProfileForm
from .models import Profile
from django.contrib.auth.views import (
    PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)

class RegisterView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = 'register.html'
    success_url = reverse_lazy('home')

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "update_profile.html"
    success_url = reverse_lazy("profile")


    def get_object(self, queryset=None):
        obj, _ = Profile.objects.get_or_create(user=self.request.user)
        return obj

    def form_valid(self, form):
        messages.success(self.request, "Профиль обновлён.")
        return super().form_valid(form)

class MyPasswordChangeView(PasswordChangeView):
    template_name = "password_change.html"
    success_url = reverse_lazy("password_change_done")

class MyPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "password_change_done.html"

class MyPasswordResetView(PasswordResetView):
    template_name = "password_reset.html"
    email_template_name = "emails/password_reset_email.txt"
    subject_template_name = "emails/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

class MyPasswordResetDoneView(PasswordResetDoneView):
    template_name = "password_reset_done.html"

class MyPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

class MyPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "password_reset_complete.html"
