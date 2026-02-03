from django.urls import path
from .views import SavedRecipeListView, SavedRecipeActionView

urlpatterns = [
    path("", SavedRecipeListView.as_view(), name='saved-recipes-list'),

    path("<int:recipe_id>/", SavedRecipeActionView.as_view(), name='saved-recipe-action'),
]