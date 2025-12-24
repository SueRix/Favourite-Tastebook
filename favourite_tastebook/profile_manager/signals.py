import contextlib
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import Profile

@receiver(post_save, sender=User)
def create_profile(instance, created, **_):
    if created:
        Profile.objects.create(user=instance)

@receiver(pre_save, sender=Profile)
def delete_old_avatar_on_change(instance, **_):
    if not instance.pk:
        return

    old = Profile.objects.filter(pk=instance.pk).first()
    if not old:
        return

    old_file = old.avatar
    new_file = instance.avatar

    if old_file and old_file != new_file:
        with contextlib.suppress(Exception):
            storage = old_file.storage
            if storage.exists(old_file.name):
                storage.delete(old_file.name)

@receiver(post_delete, sender=Profile)
def delete_avatar_on_profile_delete(instance, **_):
    avatar = instance.avatar
    if avatar:
        with contextlib.suppress(Exception):
            storage = avatar.storage
            if storage.exists(avatar.name):
                storage.delete(avatar.name)