from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("authentication.urls")),

    path("profile/", include("profile_manager.urls")),

    path("tastebook/", include("recipe_manager.urls")),
]

