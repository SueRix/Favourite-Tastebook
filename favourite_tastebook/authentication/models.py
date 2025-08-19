from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

def avatar_upload_to(instance, filename):
    return f"avatars/user_{instance.user_id}/{filename}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=150, blank=True)
    country = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, null=True)

    def __str__(self):
        return self.display_name or self.user.get_username()
