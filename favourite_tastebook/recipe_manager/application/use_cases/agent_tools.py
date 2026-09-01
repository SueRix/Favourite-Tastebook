from django.conf import settings

from recipe_manager.application.use_cases.generated_recipes import SaveGeneratedRecipeUseCase
from recipe_manager.application.use_cases.saved_recipes_dashboard import SavedRecipesUseCase
from recipe_manager.application.use_cases.search_recipes import SearchRecipesUseCase
from recipe_manager.domain.enums import AgentRecipeSource, Importance, TasteLevels, TASTE_HATE_LEVEL
from recipe_manager.domain.exceptions import (
    GeneratedRecipeAlreadySavedError,
    TabooIngredientError,
    UnknownIngredientsError,
)
from recipe_manager.domain.exceptions.saved_recipe import (
    RecipeAlreadySavedError,
    RecipeNotFoundError,
)
from recipe_manager.domain.parsers.agent_input import AgentInput
from recipe_manager.domain.parsers.generated_recipe_input import (
    ALLOWED_IMPORTANCE,
    ALLOWED_UNITS,
    GeneratedRecipeInput,
)
from recipe_manager.infrastructure.agent import AgentDraftStore
from recipe_manager.infrastructure.presentation.agent_payload import (
    AgentGeneratedRecipePresenter,
    AgentRecipePresenter,
)
from recipe_manager.infrastructure.presentation.vector_match import VectorMatchPresenter
from recipe_manager.infrastructure.selectors import (
    AgentPreferenceSelector,
    IngredientSelector,
    RecipeSelector,
)
from recipe_manager.models import Recipe, SavedRecipe, UserCuisinePreference, UserTastePreference

# The agent picks the engine, but only from the modes that already exist behind
# SearchRecipesUseCase — the tool API adds no new search semantics of its own.
SEARCH_MODES = {
    "semantic": "vector",
    "ingredient": "ingredient",
    "keyword": "keyword",
}
DEFAULT_SEARCH_MODE = "semantic"

# Beyond this many rated items the profile stops being a useful prompt and turns
# into a wall of nouns the model averages away.
MAX_TASTE_ITEMS = 40



class AgentToolsUseCase:
    """
    What: The five operations the n8n cooking agent is allowed to perform, each
          taking the raw JSON body of a tool call and returning a JSON-safe dict.
    Where: Called by the views in recipe_manager/views/agent_tool_views.py; the
           acting user always comes from the signed context, never from the body.
    Why: Tool calls are a second front door into the same domain as the web UI,
         so they reuse the existing use cases (search, saved recipes) instead of
         reimplementing them. What this layer adds is the LLM-specific contract:
         validated arguments, bounded result sizes, and business failures
         reported as data ("ok": false) rather than as HTTP errors — an agent
         needs to READ why a call failed in order to tell the user about it.
    """

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _is_authenticated(user) -> bool:
        return bool(user and getattr(user, "is_authenticated", False))

    @staticmethod
    def _failure(code: str, detail: str) -> dict:
        return {"ok": False, "error": code, "detail": detail}

    @classmethod
    def _catalogue_is_off(cls, user) -> dict | None:
        """
        The refusal the two search tools share when the user has asked for dishes
        composed by the assistant rather than looked up in our catalogue.

        Returned as data with HTTP 200 for the same reason every other business
        outcome is: the agent has to read it in order to do the right thing next,
        which here is composing a dish instead of apologising for a broken tool.
        The hint says so, because a bare refusal is what makes a model retry the
        same call.
        """
        if AgentPreferenceSelector.for_user(user)["recipe_source"] == AgentRecipeSource.DATABASE:
            return None

        return {
            "ok": False,
            "error": "database_search_disabled",
            "detail": "This user asked for dishes you compose yourself, not ones looked up in the app catalogue.",
            "hint": "Do not call the database tools. Compose the dish from your own knowledge and call propose_recipe.",
        }

    @classmethod
    def _limit(cls, payload: dict) -> int:
        return AgentInput.integer(
            payload,
            "limit",
            default=settings.AGENT_TOOL_MAX_RESULTS,
            minimum=1,
            maximum=settings.AGENT_TOOL_RESULT_CEILING,
        )

    @classmethod
    def _saved_ids(cls, user, recipe_ids) -> set:
        if not cls._is_authenticated(user) or not recipe_ids:
            return set()
        return set(
            SavedRecipe.objects
            .filter(user=user, recipe_id__in=recipe_ids)
            .values_list("recipe_id", flat=True)
        )

    # ------------------------------------------------------------------ tools

    @classmethod
    def search_recipes(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `search_recipes`: free-text recipe lookup.
        Body: {"query": str, "mode": "semantic|ingredient|keyword", "limit": int}
        """
        refusal = cls._catalogue_is_off(user)
        if refusal:
            return refusal

        query = AgentInput.text(payload, "query")
        mode = AgentInput.choice(payload, "mode", SEARCH_MODES, DEFAULT_SEARCH_MODE)
        limit = cls._limit(payload)

        recipes = SearchRecipesUseCase.execute(query, mode=SEARCH_MODES[mode], user=user)
        # attach() is a no-op for the keyword engine, which carries no similarity.
        presented = VectorMatchPresenter.attach(recipes[:limit])

        return {
            "ok": True,
            "query": query,
            "mode": mode,
            "count": len(presented),
            "recipes": AgentRecipePresenter.summary_list(presented),
        }

    @classmethod
    def recipes_by_ingredients(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `recipes_by_ingredients`: what can I cook from what I have.
        Body: {"ingredients": [str, ...], "limit": int}
        """
        refusal = cls._catalogue_is_off(user)
        if refusal:
            return refusal

        ingredients = AgentInput.string_list(payload, "ingredients")
        limit = cls._limit(payload)

        # One phrase, not one search per item: the embedding is what relates
        # "chicken, rice, carrot" to a pilaf, and N separate queries would only
        # return N unrelated single-ingredient result sets.
        query = ", ".join(ingredients)
        matches = (
            SearchRecipesUseCase.execute(query, mode=SEARCH_MODES["ingredient"], user=user)
            .prefetch_related("ingredients__ingredient")[:limit]
        )
        presented = VectorMatchPresenter.attach(matches)

        pantry = set(ingredients)
        extras = {}
        for recipe in presented:
            required = [
                ri.ingredient.name
                for ri in recipe.ingredients.all()
                if ri.importance == Importance.REQUIRED
            ]
            # Ingredient.name is normalised to lowercase on save, and AgentInput
            # lowercases the pantry, so a plain set difference is the whole match.
            missing = [name for name in required if name not in pantry]
            extras[recipe.id] = {
                "missing_required": missing,
                "missing_count": len(missing),
                "uses_from_pantry": sorted(name for name in required if name in pantry),
            }

        payload_recipes = AgentRecipePresenter.summary_list(presented, extras)
        # Similarity ranking alone would put a 6-missing-ingredient dish first.
        # For this tool "cookable tonight" beats "closest embedding", so re-rank
        # by what is actually missing; the sort is stable, so similarity order
        # survives as the tie-breaker.
        payload_recipes.sort(key=lambda item: item["missing_count"])

        return {
            "ok": True,
            "pantry": sorted(pantry),
            "count": len(payload_recipes),
            "recipes": payload_recipes,
        }

    @classmethod
    def recipe_detail(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `recipe_detail`: full ingredient list and steps for one recipe id.
        Body: {"recipe_id": int}
        """
        recipe_id = AgentInput.required_id(payload, "recipe_id")

        recipe = RecipeSelector.get_with_ingredients(recipe_id)
        if recipe is None:
            # Models hallucinate ids. Say so plainly so the agent searches again
            # instead of narrating a recipe that does not exist.
            return cls._failure("not_found", f"No recipe with id {recipe_id}.")

        is_saved = recipe_id in cls._saved_ids(user, [recipe_id])
        return {"ok": True, "recipe": AgentRecipePresenter.detail(recipe, is_saved=is_saved)}

    @classmethod
    def _empty_profile(cls, **flags) -> dict:
        return {
            "ok": True,
            "loved": [], "liked": [], "disliked": [], "never_use": [],
            "liked_cuisines": [], "disliked_cuisines": [],
            **flags,
        }

    @classmethod
    def user_tastes(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `user_tastes`: the taste profile the agent must respect.
        Body: {} — the user comes from the signed context, never from the body.
        """
        if not cls._is_authenticated(user):
            # Not an error: a guest simply has no profile, and the agent should
            # keep helping rather than reporting a failure.
            return cls._empty_profile(authenticated=False, tastes_enabled=True)

        tastes_enabled = AgentPreferenceSelector.for_user(user)["use_tastes"]

        prefs = (
            UserTastePreference.objects
            .filter(user=user)
            .exclude(score=TasteLevels.NEUTRAL)
            .select_related("ingredient")
            .order_by("ingredient__name")[:MAX_TASTE_ITEMS]
        )

        buckets = {"loved": [], "liked": [], "disliked": [], "never_use": []}
        for pref in prefs:
            name = pref.ingredient.name
            if pref.score == TASTE_HATE_LEVEL:
                # Mirrors the taboo filter used by the ranking engine: hate is a
                # hard exclusion, not a preference to weigh.
                buckets["never_use"].append(name)
            elif pref.score == TasteLevels.DISLIKE:
                buckets["disliked"].append(name)
            elif pref.score == TasteLevels.LOVE:
                buckets["loved"].append(name)
            else:
                buckets["liked"].append(name)

        if not tastes_enabled:
            # The switch says "do not shape the dish around my profile", and the
            # likes and dislikes are what shaping means, so they do not travel.
            #
            # never_use does. It is not a preference to weigh but a hard
            # exclusion — the list where an allergy is recorded — and the save
            # path rejects those ingredients whatever this switch says. Hiding
            # them here would only make the agent compose a dish that cannot be
            # kept, and then explain a refusal it was never given the means to
            # avoid.
            return cls._empty_profile(
                authenticated=True,
                tastes_enabled=False,
                never_use=buckets["never_use"],
                note=(
                    "This user turned taste personalisation off. Do not mention likes or "
                    "dislikes and do not call anything their favourite. never_use is still "
                    "binding: it carries their allergies."
                ),
            )

        cuisine_prefs = (
            UserCuisinePreference.objects
            .filter(user=user)
            .exclude(score=TasteLevels.NEUTRAL)
            .select_related("cuisine")
            .order_by("cuisine__name")[:MAX_TASTE_ITEMS]
        )
        liked_cuisines = [p.cuisine.name for p in cuisine_prefs if p.score > TasteLevels.NEUTRAL]
        disliked_cuisines = [p.cuisine.name for p in cuisine_prefs if p.score < TasteLevels.NEUTRAL]

        return {
            "ok": True,
            "authenticated": True,
            "tastes_enabled": True,
            **buckets,
            "liked_cuisines": liked_cuisines,
            "disliked_cuisines": disliked_cuisines,
        }

    @classmethod
    def save_recipe(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `save_recipe`: the only write the agent can perform.
        Body: {"recipe_id": int}
        """
        recipe_id = AgentInput.required_id(payload, "recipe_id")

        if not cls._is_authenticated(user):
            return cls._failure("auth_required", "Only a signed-in user can save recipes.")

        title = Recipe.objects.filter(id=recipe_id).values_list("title", flat=True).first()

        try:
            SavedRecipesUseCase.add_to_saved(user, recipe_id)
        except RecipeAlreadySavedError:
            # Idempotent from the point of view of the agent: the end state is
            # the one the user asked for, so a failure here would only confuse it.
            return {"ok": True, "saved": True, "already_saved": True, "title": title}
        except RecipeNotFoundError:
            return cls._failure("not_found", f"No recipe with id {recipe_id}.")

        return {"ok": True, "saved": True, "already_saved": False, "title": title}

    # -------------------------------------------------- generated recipes

    @classmethod
    def ingredient_catalog(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `ingredient_catalog`: the vocabulary a composed recipe may use.
        Body: {} — the catalogue is the same for everyone.
        """
        return {
            "ok": True,
            "ingredients": IngredientSelector.catalog_by_category(),
            "units": sorted(ALLOWED_UNITS),
            "importance": sorted(ALLOWED_IMPORTANCE),
        }

    @classmethod
    def _draft_failure(cls, exc) -> dict:
        """
        Turns the two repairable refusals into data the agent can act on.
        Shared by propose and save so a draft that was refused once is refused
        the same way twice, with the same wording.
        """
        if isinstance(exc, UnknownIngredientsError):
            # The one failure the agent can actually repair, so it gets the names
            # back and an instruction concrete enough to act on without guessing.
            return {
                "ok": False,
                "error": "unknown_ingredients",
                "detail": str(exc),
                "unknown": exc.names,
                "hint": "Call ingredient_catalog and rewrite the recipe using only names from it.",
            }
        return {
            "ok": False,
            "error": "taboo_ingredient",
            "detail": str(exc),
            "ingredients": exc.names,
            "hint": "Compose a different dish without these ingredients.",
        }

    @classmethod
    def propose_recipe(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `propose_recipe`: offers a composed dish WITHOUT saving it.
        Body: same shape as save_generated_recipe.

        The checked draft is left in the draft store under the conversation id,
        where the chat view picks it up and hands it to the studio page for the
        person to edit. Deciding to keep a recipe is theirs, not the model's.
        """
        fields = GeneratedRecipeInput.parse(payload)

        if not cls._is_authenticated(user):
            return cls._failure("auth_required", "Only a signed-in user can build recipes.")

        try:
            draft = SaveGeneratedRecipeUseCase.validate(user, **fields)
        except (UnknownIngredientsError, TabooIngredientError) as exc:
            return cls._draft_failure(exc)

        AgentDraftStore.put(session_id, draft)

        # The agent gets the normalised draft back so it describes what the
        # person is actually looking at, not the wording it had in mind.
        return {"ok": True, "proposed": True, "recipe": draft}

    @classmethod
    def save_generated_recipe(cls, payload: dict, user=None, session_id=None) -> dict:
        """
        Tool `save_generated_recipe`: keeps a dish the agent composed itself.
        Body: {"title", "cuisine", "cook_time_minutes", "steps": [...],
               "ingredients": [{"name", "amount", "unit", "importance"}, ...]}

        Downgraded to a proposal unless the user has allowed the assistant to
        put recipes away on its own — see the switch below.
        """
        fields = GeneratedRecipeInput.parse(payload)

        if not cls._is_authenticated(user):
            return cls._failure("auth_required", "Only a signed-in user can save recipes.")

        # The switch reads "allow the assistant to save recipes into your drafts
        # by itself", and this is the half of it a prompt cannot guarantee: the
        # prompt has always said to save only when asked, and the assistant
        # reaches for this tool on its own regardless.
        #
        # So the call is REDIRECTED, never refused. Refusing was tried and was
        # worse than the problem: by the time a model calls this it has already
        # composed the dish and written its answer around it, and nothing in a
        # failed tool call reliably makes it turn round and call a different
        # one. What the person saw was the assistant announcing a finished
        # recipe with no card under it and no button to press — the dish existed
        # nowhere at all.
        #
        # Offering it instead gives exactly the same card the model should have
        # asked for, with Save on it, and still writes nothing. Which tool the
        # model reached for stops mattering, which is the only version of this
        # that does not depend on the model behaving.
        if not AgentPreferenceSelector.for_user(user)["autosave_drafts"]:
            offered = cls.propose_recipe(payload, user=user, session_id=session_id)
            if not offered.get("ok"):
                # unknown_ingredients or taboo_ingredient, already worded for a
                # retry. Pass it through rather than dressing it as a save.
                return offered

            offered["saved"] = False
            offered["detail"] = (
                "This user has not allowed you to save recipes on their behalf, so the "
                "dish was offered to them instead of stored."
            )
            offered["hint"] = (
                "Tell them the recipe is ready and that they can keep it with the Save "
                "button under your message. Do not say it has been saved."
            )
            return offered

        try:
            recipe = SaveGeneratedRecipeUseCase.execute(
                user, session_id=session_id or "", **fields
            )
        except (UnknownIngredientsError, TabooIngredientError) as exc:
            return cls._draft_failure(exc)
        except GeneratedRecipeAlreadySavedError:
            # Idempotent: the end state is the one the user asked for.
            return {"ok": True, "saved": True, "already_saved": True, "title": fields["title"]}

        # The page has no way of knowing this happened — the save was a side
        # effect of a tool call on another request. Leave the new creation where
        # the chat view will find it, so the list on screen catches up with the
        # database in the same turn instead of at the next reload.
        AgentDraftStore.put_saved(session_id, AgentGeneratedRecipePresenter.editable(recipe))

        return {
            "ok": True,
            "saved": True,
            "already_saved": False,
            "recipe": AgentGeneratedRecipePresenter.detail(recipe),
        }
