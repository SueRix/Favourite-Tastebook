from django.urls import path
from .views import (
    ProfileDetailView,
    ProfileUpdateView,
    TastesView,
    CookbooksView,
    SavedRecipesView
)

urlpatterns = [
    path("profile/<str:username>/", ProfileDetailView.as_view(), name="profile_detail"),
    path("profile/<str:username>/edit/", ProfileUpdateView.as_view(), name="profile_edit"),
    path("profile/<str:username>/tastes/", TastesView.as_view(), name="tastes"),
    path("profile/<str:username>/cookbooks/", CookbooksView.as_view(), name="cookbooks"),
    path("profile/<str:username>/saved/", SavedRecipesView.as_view(), name="saved_recipes"),
]
