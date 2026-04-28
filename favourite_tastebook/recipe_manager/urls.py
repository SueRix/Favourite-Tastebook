from django.urls import path

from .views.main_views import (
    MainTastebookView,
    TastesView,
)
from .views.recipe_manager_views import (
    IngredientsPartialView,
    RecipesPartialView
)
from .views.recipe_saver_views import (
    SavedRecipeListView, SavedRecipeActionView,
)
from .views import image_ai_analyzer_view as ai_views, main_views, taste_api_views

urlpatterns = [
    path("", MainTastebookView.as_view(), name="home"),

    path("partials/ingredients/", IngredientsPartialView.as_view(), name="partials_ingredients_panel"),
    path("partials/recipes/", RecipesPartialView.as_view(), name="partials_recipes"),
    path('saved/', SavedRecipeListView.as_view(), name='saved_recipes'),
    path('saved/<int:recipe_id>/', SavedRecipeActionView.as_view(), name='saved_recipe_action'),
    path('ai/upload-form/', ai_views.AIFormView.as_view(), name='ai_upload_form'),
    path('ai/process/', ai_views.AIProcessView.as_view(), name='ai_process_image'),
    path('ai/status/<str:task_id>/', ai_views.AIStatusView.as_view(), name='ai_task_status'),
    path('tastes/', main_views.TastesView.as_view(), name='tastes_profile'),
    path('api/tastes/recipe/<int:recipe_id>/like/', taste_api_views.RecipeLikeApiView.as_view(), name='api_recipe_like'),
    path('api/tastes/ingredient/update/', taste_api_views.IngredientTasteUpdateApiView.as_view(), name='api_ingredient_update'),
]

