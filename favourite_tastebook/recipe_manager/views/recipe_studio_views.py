import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from recipe_manager.application.use_cases.generated_recipes import (
    DeleteGeneratedRecipeUseCase,
    SaveGeneratedRecipeUseCase,
)
from recipe_manager.domain.exceptions import (
    AgentPayloadError,
    GeneratedRecipeAlreadySavedError,
    GeneratedRecipeNotFoundError,
    TabooIngredientError,
    UnknownIngredientsError,
)
from recipe_manager.domain.parsers.generated_recipe_input import (
    ALLOWED_IMPORTANCE,
    ALLOWED_UNITS,
    GeneratedRecipeInput,
)
from recipe_manager.infrastructure.agent import AgentChatSession
from recipe_manager.infrastructure.presentation.agent_payload import AgentGeneratedRecipePresenter
from recipe_manager.infrastructure.selectors import GeneratedRecipeSelector, IngredientSelector
from recipe_manager.views.agent_chat_views import JsonLoginRequiredMixin

logger = logging.getLogger(__name__)


class RecipeStudioView(LoginRequiredMixin, TemplateView):
    """
    The page where a dish gets invented: a conversation on the left, the recipe
    it is producing on the right, editable before it is kept.

    Signed-in only, and not merely because saving needs an owner. The whole point
    of the conversation is a dish shaped around THIS person's taste profile, and
    for a guest there is no profile to shape it around — the agent would have
    nothing to work with beyond the message itself.
    """

    template_name = "main/recipe_studio.html"

    @staticmethod
    def creations(user) -> list[dict]:
        """
        The user's creations in the shape the editor speaks.

        Both the first render and every later refresh go through here, so the
        list the page starts with and the list it fetches after a save can never
        drift into two different shapes.
        """
        return [
            AgentGeneratedRecipePresenter.editable(recipe)
            for recipe in GeneratedRecipeSelector.list_for_user(user)
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # The catalogue goes into the page so an edited row can only ever name an
        # ingredient the save will accept. It is ~120 names: cheaper to ship once
        # than to ask for on every keystroke.
        context["ingredient_catalog"] = IngredientSelector.catalog_by_category()
        context["units"] = sorted(ALLOWED_UNITS)
        context["importance_levels"] = sorted(ALLOWED_IMPORTANCE)
        context["chat_id"] = AgentChatSession.current(self.request.session)
        # Past creations travel in the same shape as a fresh draft, so opening
        # one puts it straight into the editor with no special case.
        context["my_recipes"] = self.creations(self.request.user)
        return context


class RecipeStudioSaveView(JsonLoginRequiredMixin, View):
    """
    POST /home/studio/save/ — keep the recipe currently on screen.

    The body is the draft as the person edited it, in the same shape the agent
    proposes. It goes through the same parser and the same use case as the
    agent's own save: editing the draft must not be a way around the checks the
    tool would have applied, in particular the never_use list.
    """

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"error": "bad_request", "detail": "Malformed recipe."}, status=400)

        if not isinstance(payload, dict):
            return JsonResponse({"error": "bad_request", "detail": "Malformed recipe."}, status=400)

        try:
            fields = GeneratedRecipeInput.parse(payload)
        except AgentPayloadError as exc:
            # These are edits a person made, so the message is theirs to read.
            return JsonResponse({"error": "invalid", "detail": str(exc)}, status=400)

        try:
            recipe = SaveGeneratedRecipeUseCase.execute(
                request.user,
                session_id=AgentChatSession.current(request.session),
                **fields,
            )
        except UnknownIngredientsError as exc:
            return JsonResponse(
                {"error": "unknown_ingredients", "detail": exc.message, "unknown": exc.names},
                status=400,
            )
        except TabooIngredientError as exc:
            return JsonResponse(
                {"error": "taboo_ingredient", "detail": exc.message, "ingredients": exc.names},
                status=400,
            )
        except GeneratedRecipeAlreadySavedError as exc:
            return JsonResponse({"error": "already_saved", "detail": exc.message}, status=409)

        return JsonResponse({"status": "success", "recipe_id": recipe.id, "title": recipe.title})


class RecipeStudioCreationsView(JsonLoginRequiredMixin, View):
    """
    GET /home/studio/creations/ — the user's creations as they stand right now.

    The page ships the list once with the HTML, and that copy goes stale the
    moment anything is written: the agent may save a dish from inside a chat
    turn, and a second tab may add or drop one. Rather than teaching the browser
    to patch its copy for each of those, every write is followed by a re-read of
    the truth. One indexed query per event is cheaper than a class of bugs where
    the list on screen and the database disagree.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse({"recipes": RecipeStudioView.creations(request.user)})


class RecipeStudioCreationDeleteView(JsonLoginRequiredMixin, View):
    """
    DELETE /home/studio/creations/<id>/ — drop one creation.

    Ownership is enforced inside the use case, which looks the recipe up BY
    owner: somebody else's id answers 404, exactly as an id that never existed
    would, so this endpoint tells a caller nothing about recipes that are not
    theirs.
    """

    def delete(self, request, recipe_id, *args, **kwargs):
        try:
            title = DeleteGeneratedRecipeUseCase.execute(request.user, recipe_id)
        except GeneratedRecipeNotFoundError as exc:
            return JsonResponse({"error": "not_found", "detail": exc.message}, status=404)

        return JsonResponse({"status": "success", "recipe_id": recipe_id, "title": title})
