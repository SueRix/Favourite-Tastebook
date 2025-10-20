import re
from django.contrib.auth.forms import PasswordChangeForm
from .models import Profile
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

User = get_user_model()

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")
USERNAME_MIN = 3
USERNAME_MAX = 30

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_MB = 3


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "country", "avatar"]

    def clean_display_name(self):
        name = (self.cleaned_data.get("display_name") or "").strip()
        if len(name) > 150:
            raise forms.ValidationError("Display name is too long (max 150).")
        return name

    def clean_country(self):
        country = (self.cleaned_data.get("country") or "").strip()
        if len(country) > 100:
            raise forms.ValidationError("Country is too long (max 100).")
        return country

    def clean_avatar(self):
        f = self.cleaned_data.get("avatar")
        if not f:
            return f
        ctype = getattr(f, "content_type", "")
        if ctype not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError("Only JPEG, PNG or WebP images are allowed.")
        if f.size > MAX_AVATAR_MB * 1024 * 1024:
            raise forms.ValidationError(f"Avatar size must be ≤ {MAX_AVATAR_MB} MB.")
        return f


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        user = self.instance

        if username == user.username:
            return username

        if User.objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
            raise forms.ValidationError("This username is already taken.")

        profile = getattr(user, "profile", None)
        if profile is None:
            from .models import Profile
            profile, _ = Profile.objects.get_or_create(user=user)

        if not profile.can_change_username():
            raise forms.ValidationError("You can change your username only once every 30 days.")

        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        username_changed = user.pk and "username" in self.changed_data

        if commit:
            user.save()
            if username_changed:
                profile = getattr(user, "profile", None)
                if profile is None:
                    from .models import Profile
                    profile, _ = Profile.objects.get_or_create(user=user)
                profile.last_username_change_at = timezone.now()
                profile.save()
        return user


class PasswordUpdateForm(PasswordChangeForm):
    old_password = forms.CharField(label="Current password", widget=forms.PasswordInput)
    new_password1 = forms.CharField(label="New password", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Confirm new password", widget=forms.PasswordInput)

    def clean_new_password1(self):
        new = self.cleaned_data.get("new_password1")
        old = self.cleaned_data.get("old_password")
        if old and new and old == new:
            raise forms.ValidationError("New password must differ from the current password.")
        return new


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email is already in use.")
        return email
