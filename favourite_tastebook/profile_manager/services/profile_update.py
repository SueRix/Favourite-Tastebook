from dataclasses import dataclass
from typing import Any
from django.contrib.auth import get_user_model

from ..crud.profile import get_or_create_profile_for_user
from ..forms import ProfileForm, UserUpdateForm

User = get_user_model()

@dataclass(frozen=True)
class UpdateOutcome:
    user_form: UserUpdateForm
    profile_form: ProfileForm
    saved: bool

def build_forms(*, user: User, method: str, post: Any = None, files: Any = None):
    profile = get_or_create_profile_for_user(user=user)

    if method == "POST":
        return (
            UserUpdateForm(post, instance=user),
            ProfileForm(post, files, instance=profile),
        )

    return (
        UserUpdateForm(instance=user),
        ProfileForm(instance=profile),
    )

def submit(*, user: User, post: Any, files: Any) -> UpdateOutcome:
    user_form, profile_form = build_forms(user=user, method="POST", post=post, files=files)

    if user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        return UpdateOutcome(user_form=user_form, profile_form=profile_form, saved=True)

    return UpdateOutcome(user_form=user_form, profile_form=profile_form, saved=False)
