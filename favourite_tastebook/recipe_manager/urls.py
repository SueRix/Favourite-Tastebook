from django.urls import path

from .views import (
    MainTastebookView,
    IngredientsPartialView,
    SelectedIngredientsPartialView,
    RecipesPartialView,
)

urlpatterns = [
    path("", MainTastebookView.as_view(), name="home"),

    path("partials/ingredients/", IngredientsPartialView.as_view(), name="partials_ingredients"),
    path("partials/selected/", SelectedIngredientsPartialView.as_view(), name="partials_selected"),
    path("partials/recipes/", RecipesPartialView.as_view(), name="partials_recipes"),
]
