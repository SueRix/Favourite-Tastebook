import os
import uuid
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

def avatar_upload_to(instance, filename):
    base, ext = os.path.splitext(filename)
    ext = (ext or ".png").lower()
    return f"avatars/{instance.user_id}/{uuid.uuid4().hex}{ext}"

class Profile(models.Model):
    class Country(models.TextChoices):
        UKRAINE = 'UA', 'Ukraine'
        USA = 'US', 'United States'
        ITALY = 'IT', 'Italy'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    avatar = models.ImageField(
        upload_to=avatar_upload_to,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])],
        help_text="JPG/PNG/JPEG"
    )

    country = models.CharField(
        max_length=2,
        choices=Country.choices,
        default=Country.UKRAINE,
        blank=True,
        verbose_name="Preferred Cuisine / Region"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile({self.user.username})"

    def get_absolute_url(self):
        return reverse("profile_detail")