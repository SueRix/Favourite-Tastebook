from django import forms
from .models import Profile

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_MB = 3

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "country", "avatar"]

    def clean_avatar(self):
        file = self.cleaned_data.get("avatar")
        if not file:
            return file
        if getattr(file, "content_type", None) not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError("Only JPEG/PNG/WebP!")
        if file.size > MAX_AVATAR_MB * 1024 * 1024:
            raise forms.ValidationError(f"Max avatars size {MAX_AVATAR_MB} МБ.")
        return file
