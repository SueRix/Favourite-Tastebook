from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from .models import Profile
from .forms import UserUpdateForm, ProfileForm


class ProfileUpdateView(LoginRequiredMixin, View):
    template_name = "profile/edit.html"

    def get(self, request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)

        # bind data to forms
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()

            # return with success flag
            return render(request, self.template_name, {
                'user_form': user_form,
                'profile_form': profile_form,
                'saved': True
            })

        # return with errors
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form,
            'errors': True
        }, status=400)