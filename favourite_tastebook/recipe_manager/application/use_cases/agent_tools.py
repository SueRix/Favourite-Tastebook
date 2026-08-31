from django.conf import settings

from recipe_manager.application.use_cases.generated_recipes import SaveGeneratedRecipeUseCase
from recipe_manager.application.use_cases.saved_recipes_dashboard import SavedRecipesUseCase
from recipe_manager.application.use_cases.search_recipes import SearchRecipesUseCase
from recipe_manager.domain.enums import Importance, TasteLevels, TASTE_HATE_LEVEL, Units
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
from recipe_manager.infrastructure.presentation.agent_payload import (
    AgentGeneratedRecipePresenter,
    AgentRecipePresenter,
)
from recipe_manager.infrastructure.presentation.vector_match import VectorMatchPresenter
from recipe_manager.infrastructure.selectors import IngredientSelector, RecipeSelector
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

# The agent composes dishes from its own knowledge, but the parts have to be ones
# we know: only then can a saved recipe be checked against the taboo list and
# still take part in the taste mechanics. These are the vocabularies it may use.
ALLOWED_UNITS = {value: value for value in Units.values}
ALLOWED_IMPORTANCE = {value: value for value in Importance.values}

# A dish nobody can cook in a day is a hallucinated number, not a slow roast.
MAX_GENERATED_COOK_TIME = 1440
DEFAULT_GENERATED_COOK_TIME = 30


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
    def search_recipes(cls, payload: dict, user=None) -> dict:
        """
        Tool `search_recipes`: free-text recipe lookup.
        Body: {"query": str, "mode": "semantic|ingredient|keyword", "limit": int}
        """
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
    def recipes_by_ingredients(cls, payload: dict, user=None) -> dict:
        """
        Tool `recipes_by_ingredients`: what can I cook from what I have.
        Body: {"ingredients": [str, ...], "limit": int}
        """
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
    def recipe_detail(cls, payload: dict, user=None) -> dict:
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
    def user_tastes(cls, payload: dict, user=None) -> dict:
        """
        Tool `user_tastes`: the taste profile the agent must respect.
        Body: {} — the user comes from the signed context, never from the body.
        """
        if not cls._is_authenticated(user):
            # Not an error: a guest simply has no profile, and the agent should
            # keep helping rather than reporting a failure.
            return {
                "ok": True,
                "authenticated": False,
                "loved": [], "liked": [], "disliked": [], "never_use": [],
                "liked_cuisines": [], "disliked_cuisines": [],
            }

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
            **buckets,
            "liked_cuisines": liked_cuisines,
            "disliked_cuisines": disliked_cuisines,
        }

    @classmethod
    def save_recipe(cls, payload: dict, user=None) -> dict:
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
    def ingredient_catalog(cls, payload: dict, user=None) -> dict:
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
    def _ingredient_line(cls, line: dict) -> dict:
        """One {name, amount, unit, importance} entry of a composed recipe."""
        return {
            # Ingredient.name is stored lowercase, so match on the same form.
            "name": AgentInput.text(line, "name", max_length=100).lower(),
            "amount": AgentInput.amount(line, "amount"),
            "unit": AgentInput.choice(line, "unit", ALLOWED_UNITS, Units.GRAM),
            "importance": AgentInput.choice(
                line, "importance", ALLOWED_IMPORTANCE, Importance.REQUIRED
            ),
        }

    @classmethod
    def save_generated_recipe(cls, payload: dict, user=None) -> dict:
        """
        Tool `save_generated_recipe`: keeps a dish the agent composed itself.
        Body: {"title", "cuisine", "cook_time_minutes", "steps": [...],
               "ingredients": [{"name", "amount", "unit", "importance"}, ...]}
        """
        title = AgentInput.text(payload, "title", max_length=255)
        cuisine = AgentInput.text(payload, "cuisine", required=False, max_length=100)
        cook_time = AgentInput.integer(
            payload,
            "cook_time_minutes",
            default=DEFAULT_GENERATED_COOK_TIME,
            minimum=1,
            maximum=MAX_GENERATED_COOK_TIME,
        )
        steps = AgentInput.paragraph_list(payload, "steps")
        lines = [cls._ingredient_line(line) for line in AgentInput.object_list(payload, "ingredients")]

        if not cls._is_authenticated(user):
            return cls._failure("auth_required", "Only a signed-in user can save recipes.")

        try:
            recipe = SaveGeneratedRecipeUseCase.execute(
                user,
                title=title,
                cuisine=cuisine,
                cook_time=cook_time,
                steps=steps,
                ingredient_lines=lines,
            )
        except UnknownIngredientsError as exc:
            # The one failure the agent can actually repair, so it gets the names
            # back and an instruction concrete enough to act on without guessing.
            return {
                "ok": False,
                "error": "unknown_ingredients",
                "detail": str(exc),
                "unknown": exc.names,
                "hint": "Call ingredient_catalog and rewrite the recipe using only names from it.",
            }
        except TabooIngredientError as exc:
            return {
                "ok": False,
                "error": "taboo_ingredient",
                "detail": str(exc),
                "ingredients": exc.names,
                "hint": "Compose a different dish without these ingredients.",
            }
        except GeneratedRecipeAlreadySavedError:
            # Idempotent: the end state is the one the user asked for.
            return {"ok": True, "saved": True, "already_saved": True, "title": title}

        return {
            "ok": True,
            "saved": True,
            "already_saved": False,
            "recipe": AgentGeneratedRecipePresenter.detail(recipe),
        }
