from django import forms
from django.contrib.auth.models import User
from profile_manager.models import Profile
from django.conf import settings

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last Name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already in use by another account.")
        return email


class ProfileForm(forms.ModelForm):
    remove_avatar = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'checkbox-input'})
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'country']
        widgets = {
            "country": forms.Select(attrs={'class': 'form-select'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.cleaned_data.get("remove_avatar"):
            if instance.avatar:
                try:
                    storage = instance.avatar.storage
                    if storage.exists(instance.avatar.name):
                        storage.delete(instance.avatar.name)
                except Exception:
                    pass
            instance.avatar = None

        if commit:
            instance.save()
            self.instance.refresh_from_db()
        return instance

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and hasattr(settings, 'MAX_AVATAR_MB'):
            if avatar.size > settings.MAX_AVATAR_MB * 1024 * 1024:
                raise forms.ValidationError(f"Avatar must be less than {settings.MAX_AVATAR_MB} MB")
        return avatar