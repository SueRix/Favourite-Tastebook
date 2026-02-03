from django.urls import path

from .views import (
    MainTastebookView,
    IngredientsPartialView,
    SelectedIngredientsPartialView,
    RecipesPartialView, IngredientSearchView,
    SavedRecipeListView, SavedRecipeActionView,
    TastesView,
    CookbooksView,
)

urlpatterns = [
    path("", MainTastebookView.as_view(), name="home"),

    path("partials/ingredients/", IngredientsPartialView.as_view(), name="partials_ingredients"),
    path("partials/selected/", SelectedIngredientsPartialView.as_view(), name="partials_selected"),
    path("partials/recipes/", RecipesPartialView.as_view(), name="partials_recipes"),
    path('ingredients/search/', IngredientSearchView.as_view(), name='ingredient_search_results'),
    path('saved/', SavedRecipeListView.as_view(), name='saved_recipes'),
    path('saved/<int:recipe_id>/', SavedRecipeActionView.as_view(), name='saved_recipe_action'),
    path("tastes/", TastesView.as_view(), name="tastes"),
    path("cookbooks/", CookbooksView.as_view(), name="cookbooks"),
]