from django.urls import path
from .views import (
    ProfileDetailView,
    ProfileUpdateView,
    TastesView,
    CookbooksView,
    SavedRecipesView
)

urlpatterns = [
    path("profile/", ProfileDetailView.as_view(), name="profile_detail"),
    path("profile/edit/", ProfileUpdateView.as_view(), name="profile_edit"),

    path("profile/tastes/", TastesView.as_view(), name="tastes"),
    path("profile/cookbooks/", CookbooksView.as_view(), name="cookbooks"),
    path("profile/saved/", SavedRecipesView.as_view(), name="saved_recipes"),
]