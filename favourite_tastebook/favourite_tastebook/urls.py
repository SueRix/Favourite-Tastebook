from django.conf import settings
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # auth
    path("accounts/", include("authentication.urls")),

    # profile
    path("profile/", include("profile_manager.urls")),

    # tastebook / recipes
    path("tastebook/", include("recipe_manager.urls")),
]

