from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from recipe_manager.application.use_cases.agent_tools import AgentToolsUseCase
from recipe_manager.infrastructure.agent.auth import agent_tool


@method_decorator(csrf_exempt, name="dispatch")
class BaseAgentToolView(View):
    """
    What: Shared shell for the n8n tool endpoints — one POST, one use-case call.
    Where: Subclassed by the five views mounted under /api/agent/tools/.
    Why: These are server-to-server calls carrying no session cookie, so CSRF
         protection has nothing to protect and would only reject every call; the
         X-Agent-Token header is what authenticates the caller instead. Keeping
         the exemption on one base class makes that decision reviewable in a
         single place rather than repeated five times.

    Subclasses only declare `tool`, so the view layer stays free of any logic
    the way the rest of the project keeps it.
    """

    #: Callable(payload, user=..., session_id=...) -> dict, set by each subclass.
    #: Every tool takes the same three arguments even when it ignores the last
    #: two, so this base class never has to know which is which.
    tool = None

    @agent_tool
    def post(self, request, *args, **kwargs):
        result = type(self).tool(
            request.agent_payload,
            user=request.agent_user,
            session_id=request.agent_session_id,
        )
        return JsonResponse(result)


class AgentSearchRecipesView(BaseAgentToolView):
    """Tool `search_recipes` — free-text lookup over the recipe database."""
    tool = AgentToolsUseCase.search_recipes


class AgentRecipesByIngredientsView(BaseAgentToolView):
    """Tool `recipes_by_ingredients` — what the user can cook from a pantry list."""
    tool = AgentToolsUseCase.recipes_by_ingredients


class AgentRecipeDetailView(BaseAgentToolView):
    """Tool `recipe_detail` — ingredients and steps for one recipe id."""
    tool = AgentToolsUseCase.recipe_detail


class AgentUserTastesView(BaseAgentToolView):
    """Tool `user_tastes` — likes, dislikes and hard exclusions of the chatting user."""
    tool = AgentToolsUseCase.user_tastes


class AgentSaveRecipeView(BaseAgentToolView):
    """Tool `save_recipe` — the single write the agent is allowed to perform."""
    tool = AgentToolsUseCase.save_recipe


class AgentIngredientCatalogView(BaseAgentToolView):
    """Tool `ingredient_catalog` — the ingredient vocabulary a composed recipe may use."""
    tool = AgentToolsUseCase.ingredient_catalog


class AgentProposeRecipeView(BaseAgentToolView):
    """Tool `propose_recipe` — offers a composed dish for the person to edit and keep."""
    tool = AgentToolsUseCase.propose_recipe


class AgentSaveGeneratedRecipeView(BaseAgentToolView):
    """Tool `save_generated_recipe` — stores a dish the agent composed itself."""
    tool = AgentToolsUseCase.save_generated_recipe
