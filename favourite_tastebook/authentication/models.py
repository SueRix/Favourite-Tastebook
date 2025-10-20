from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def avatar_upload_to(instance, filename):
    return f"avatars/user_{instance.user_id}/{filename}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=64, blank=True)
    country = models.CharField(max_length=2, blank=True)
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, null=True)

    last_username_change_at = models.DateTimeField(null=True, blank=True)

    def can_change_username(self) -> bool:
        #cd 30 days
        if not self.last_username_change_at:
            return True
        return (timezone.now() - self.last_username_change_at).days >= 30
