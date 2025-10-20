# authentication/urls.py
from django.urls import path
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView
)
from .views import RegisterView, UpdateProfileView

urlpatterns = [
    path("accounts/register/", RegisterView.as_view(), name="register"),
    path("accounts/login/",  LoginView.as_view(template_name="authentication/login.html"), name="login"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),

    path(
        "accounts/password_change/",
        PasswordChangeView.as_view(
            template_name="authentication/password_change.html",
            success_url="/accounts/password_change/done/"
        ),
        name="password_change",
    ),
    path(
        "accounts/password_change/done/",
        PasswordChangeDoneView.as_view(template_name="authentication/password_change_done.html"),
        name="password_change_done",
    ),

    path("accounts/profile/", UpdateProfileView.as_view(), name="profile"),
]
