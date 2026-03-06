from django.urls import path

from .views.main_views import (
    MainTastebookView,
    TastesView,
)
from .views.recipe_manager_views import (
    IngredientsPartialView,
    RecipesPartialView, IngredientSearchView,
)
from .views.recipe_saver_views import (
    SavedRecipeListView, SavedRecipeActionView,
)

urlpatterns = [
    path("", MainTastebookView.as_view(), name="home"),

    path("partials/ingredients/", IngredientsPartialView.as_view(), name="partials_ingredients_panel"),
    path("partials/recipes/", RecipesPartialView.as_view(), name="partials_recipes"),
    path('ingredients/search/', IngredientSearchView.as_view(), name='ingredient_search_results'),
    path('saved/', SavedRecipeListView.as_view(), name='saved_recipes'),
    path('saved/<int:recipe_id>/', SavedRecipeActionView.as_view(), name='saved_recipe_action'),
    path("tastes/", TastesView.as_view(), name="tastes"),
]
