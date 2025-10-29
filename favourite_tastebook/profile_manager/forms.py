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
    remove_avatar = forms.BooleanField(required=False, initial=False, help_text="Remove current avatar")

    class Meta:
        model = Profile
        fields = ['display_name', 'avatar', "country", "bio", "birth_date", "gender"]
        widgets = {
            "birth_date": forms.TextInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 5}),
        }

    GENDER_ALIASES = {
        "F": "FEMALE",
        "M": "MALE",
        "U": "Unspecified",
        "Female": "FEMALE",
        "Male": "MALE",
        "UNSPECIFIED": "Unspecified",
    }

    def clean_gender(self):
        value = self.cleaned_data.get("gender")
        if value in self.GENDER_ALIASES:
            return self.GENDER_ALIASES[value]
        return value

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
        if avatar and avatar.size > settings.MAX_AVATAR_MB * 1024 * 1024:
            raise forms.ValidationError(f"Avatar must be less than {settings.MAX_AVATAR_MB} MB")
        return avatar

    def clean_bio(self):
        bio = self.cleaned_data.get("bio", "")
        if bio and len(bio) > settings.MAX_BIO_LEN:
            raise forms.ValidationError(f"Bio must be ≤ {settings.MAX_BIO_LEN} characters.")
        return bio
