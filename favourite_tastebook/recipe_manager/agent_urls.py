"""
Tool surface exposed to the self-hosted n8n cooking agent.

Mounted at /api/agent/ from the project urlconf — deliberately NOT under the
`home/` prefix that serves the browser-facing views, so the whole agent API can
be firewalled, logged or rate-limited as one path.

Every endpoint is POST-only, takes a JSON object and answers a JSON object.
Two headers are mandatory on all of them (see infrastructure/agent/auth.py):

    X-Agent-Token    shared secret proving the caller is our own n8n
    X-Agent-Context  signed {uid, sid} minted by the chat view; identifies the
                     acting user. Never a body field: the LLM must not be able
                     to choose whose profile it reads or writes.

Contract, in the order the agent normally uses them:

    POST tools/tastes/            {}                      -> loved/liked/disliked/never_use
    POST tools/search-recipes/    {query, mode?, limit?}   -> [{id, title, match_percent, ...}]
    POST tools/by-ingredients/    {ingredients[], limit?}  -> the same plus missing_required
    POST tools/recipe-detail/     {recipe_id}              -> steps + grouped ingredients
    POST tools/save-recipe/       {recipe_id}              -> {saved, already_saved}

Composing a dish the database does not have is the agent's main job, and it uses
two more endpoints for that:

    POST tools/ingredient-catalog/ {}                      -> {ingredients, units, importance}
    POST tools/propose-recipe/    {the composed recipe}    -> the checked draft, unsaved
    POST tools/save-generated-recipe/ {title, cook_time_minutes, steps[], ingredients[]}
                                                           -> the stored recipe

Three of these endpoints answer differently depending on what the user set in the
studio's settings panel (see recipe_manager/models.py, AgentPreference):

    recipe_source = "ai"   search-recipes/ and by-ingredients/ answer
                           {"ok": false, "error": "database_search_disabled"}
                           without reaching the search engine at all.
    use_tastes = False     tastes/ answers with empty loved/liked/disliked. The
                           never_use list still travels, because it is a hard
                           exclusion the save path enforces regardless.
    autosave_drafts=False  save-generated-recipe/ stores nothing and answers as
                           propose-recipe/ would (proposed: true, saved: false),
                           so the dish still reaches the person as a card.

The switches also travel to the workflow in the chat payload so the prompt can
describe them, but that is a courtesy to the model. The refusals above are what
actually holds, and they hold whatever the model was talked into.

Note that APPEND_SLASH is off project-wide, so the trailing slash is part of
each URL and the n8n HTTP Request nodes must include it.
"""

from django.urls import path

from recipe_manager.views.agent_tool_views import (
    AgentIngredientCatalogView,
    AgentProposeRecipeView,
    AgentRecipeDetailView,
    AgentRecipesByIngredientsView,
    AgentSaveGeneratedRecipeView,
    AgentSaveRecipeView,
    AgentSearchRecipesView,
    AgentUserTastesView,
)

urlpatterns = [
    path("tools/search-recipes/", AgentSearchRecipesView.as_view(), name="agent_tool_search_recipes"),
    path("tools/by-ingredients/", AgentRecipesByIngredientsView.as_view(), name="agent_tool_by_ingredients"),
    path("tools/recipe-detail/", AgentRecipeDetailView.as_view(), name="agent_tool_recipe_detail"),
    path("tools/tastes/", AgentUserTastesView.as_view(), name="agent_tool_user_tastes"),
    path("tools/save-recipe/", AgentSaveRecipeView.as_view(), name="agent_tool_save_recipe"),
    path(
        "tools/ingredient-catalog/",
        AgentIngredientCatalogView.as_view(),
        name="agent_tool_ingredient_catalog",
    ),
    path(
        "tools/propose-recipe/",
        AgentProposeRecipeView.as_view(),
        name="agent_tool_propose_recipe",
    ),
    path(
        "tools/save-generated-recipe/",
        AgentSaveGeneratedRecipeView.as_view(),
        name="agent_tool_save_generated_recipe",
    ),
]
