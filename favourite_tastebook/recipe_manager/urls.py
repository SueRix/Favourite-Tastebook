from django.urls import path

from .views import (
    MainTastebookView,
    IngredientsPartialView,
    SelectedIngredientsPartialView,
    RecipesPartialView,
)

urlpatterns = [
    path("", MainTastebookView.as_view(), name="tastebook_main"),

    path("_partials/ingredients/", IngredientsPartialView.as_view(), name="partials_ingredients"),
    path("_partials/selected/", SelectedIngredientsPartialView.as_view(), name="partials_selected"),
    path("_partials/recipes/", RecipesPartialView.as_view(), name="partials_recipes"),
]
