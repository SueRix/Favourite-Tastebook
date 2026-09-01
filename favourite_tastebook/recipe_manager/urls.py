from django.urls import path

from .views.main_views import (
    MainTastebookView,
)
from .views.recipe_manager_views import (
    IngredientsPartialView,
    RecipesPartialView,
)
from .views.recipe_database_search_views import (
    RecipesDatabaseView,
    RecipesDatabaseSearchPartialView,
    RecipesDatabaseCardPartialView,
)
from .views.agent_chat_views import (
    AgentChatResetView,
    AgentChatView,
)
from .views.recipe_studio_views import (
    RecipeStudioCreationDeleteView,
    RecipeStudioCreationsView,
    RecipeStudioSaveView,
    RecipeStudioView,
)
from .views.recipe_saver_views import (
    SavedRecipeListView, SavedRecipeActionView,
)
from .views import image_ai_analyzer_view as ai_views, main_views, taste_api_views
from .views.taste_api_views import CuisineTasteUpdateApiView

urlpatterns = [
    path("", MainTastebookView.as_view(), name="home"),

    # Cooking agent. The browser talks only to these two: neither the service
    # token nor the signed context ever reaches the page.
    path("chat/", AgentChatView.as_view(), name="agent_chat"),
    path("chat/reset/", AgentChatResetView.as_view(), name="agent_chat_reset"),
    path("studio/", RecipeStudioView.as_view(), name="recipe_studio"),
    path("studio/save/", RecipeStudioSaveView.as_view(), name="recipe_studio_save"),
    path("studio/creations/", RecipeStudioCreationsView.as_view(), name="recipe_studio_creations"),
    path(
        "studio/creations/<int:recipe_id>/",
        RecipeStudioCreationDeleteView.as_view(),
        name="recipe_studio_creation_delete",
    ),

    path("partials/ingredients/", IngredientsPartialView.as_view(), name="partials_ingredients_panel"),
    path("partials/recipes/", RecipesPartialView.as_view(), name="partials_recipes"),
    path('saved/', SavedRecipeListView.as_view(), name='saved_recipes'),
    path('saved/<int:recipe_id>/', SavedRecipeActionView.as_view(), name='saved_recipe_action'),
    path('ai/upload-form/', ai_views.AIFormView.as_view(), name='ai_upload_form'),
    path('ai/process/', ai_views.AIProcessView.as_view(), name='ai_process_image'),
    path('ai/status/<str:task_id>/', ai_views.AIStatusView.as_view(), name='ai_task_status'),
    path('tastes/', main_views.TastesView.as_view(), name='tastes_profile'),
    path('api/tastes/recipe/<int:recipe_id>/like/', taste_api_views.RecipeLikeApiView.as_view(),
         name='api_recipe_like'),
    path('api/tastes/recipe/<int:recipe_id>/dislike/', taste_api_views.RecipeDislikeApiView.as_view(),
        name='api_recipe_dislike'),
    path('api/tastes/ingredient/update/', taste_api_views.IngredientTasteUpdateApiView.as_view(),
         name='api_ingredient_update'),
    path('partials/tastes/rated/', taste_api_views.RatedTastesPartialView.as_view(), name='partials_rated_tastes'),
    path('partials/tastes/search/', taste_api_views.SearchTastesPartialView.as_view(), name='partials_search_tastes'),
    path('api/tastes/toggle-global/', taste_api_views.ToggleGlobalTasteApiView.as_view(),
         name='api_toggle_global_tastes'),
    path('api/taste/cuisine/update/', CuisineTasteUpdateApiView.as_view(), name='api_cuisine_taste_update'),

    path("database/", RecipesDatabaseView.as_view(), name="recipes_database"),
    path(
        "partials/database/search/",
        RecipesDatabaseSearchPartialView.as_view(),
        name="partials_recipes_database_search",
    ),
    path(
        "partials/database/card/<int:recipe_id>/",
        RecipesDatabaseCardPartialView.as_view(),
        name="partials_recipes_database_card",
    ),
]
