from django import forms
from django.contrib.auth.models import User
from profile_manager.models import Profile


class UserUpdateForm(forms.ModelForm):
    class Meta:
        models = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last Name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email"}),
        }


class ProfileForm(forms.ModelForm):
    MAX_AVATAR_MB = 5

    class Meta:
        model = Profile
        fields = ['display_name',
                  'avatar',
                  "country",
                  "bio",
                  "birth_date",
                  "gender",
                  ]
        widgets = {
            "birth_date": forms.TextInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and avatar.size > self.MAX_AVATAR_MB * 1024 * 1024:
            raise forms.ValidationError(f"Avatar must be less than {self.MAX_AVATAR_MB} MB")
        return avatar
