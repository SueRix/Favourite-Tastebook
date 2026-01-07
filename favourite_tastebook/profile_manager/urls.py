from django.urls import path
from .views import (
    ProfileDetailView,
    ProfileUpdateView,
    TastesView,
    CookbooksView,
    SavedRecipesView
)

urlpatterns = [
    path("", ProfileDetailView.as_view(), name="profile_detail"),
    path("edit/", ProfileUpdateView.as_view(), name="profile_edit"),

    path("tastes/", TastesView.as_view(), name="tastes"),
    path("cookbooks/", CookbooksView.as_view(), name="cookbooks"),
    path("saved/", SavedRecipesView.as_view(), name="saved_recipes"),
]