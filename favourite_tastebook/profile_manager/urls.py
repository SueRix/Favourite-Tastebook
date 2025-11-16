from django.urls import path
from .views import (
    ProfileDetailView,
    ProfileUpdateView
)

urlpatterns = [
    path("profile/<str:username>/", ProfileDetailView.as_view(), name="profile_detail"),
    path("profile/<str:username>/edit/", ProfileUpdateView.as_view(), name="profile_edit"),
]
