from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from ..crud.profile import get_or_create_profile_for_user
from ..services.profile_update import build_forms, submit


@login_required
def profile_detail(request: HttpRequest) -> HttpResponse:
    profile = get_or_create_profile_for_user(user=request.user)
    return render(request, "profile/detail.html", {"profile": profile})


@login_required
def profile_edit(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        outcome = submit(user=request.user, post=request.POST, files=request.FILES)

        if outcome.saved:
            return render(
                request,
                "profile/edit.html",
                {"user_form": outcome.user_form, "profile_form": outcome.profile_form, "saved": True},
            )

        return render(
            request,
            "profile/edit.html",
            {
                "user_form": outcome.user_form,
                "profile_form": outcome.profile_form,
                "errors": {"user": outcome.user_form.errors, "profile": outcome.profile_form.errors},
            },
            status=400,
        )

    user_form, profile_form = build_forms(user=request.user, method="GET")
    return render(request, "profile/edit.html", {"user_form": user_form, "profile_form": profile_form})
