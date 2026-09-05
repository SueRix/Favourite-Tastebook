from recipe_manager.domain.enums import Importance
from recipe_manager.domain.parsers.recipe_steps import RecipeStepsParser

# Everything a tool returns is paid for twice: once as prompt tokens on the way
# into the model, once as latency. These caps keep a single tool call cheap.
MAX_DESCRIPTION_CHARS = 180
MAX_STEPS = 20
MAX_INGREDIENTS = 40

IMPORTANCE_GROUPS = (
    ("required", Importance.REQUIRED),
    ("secondary", Importance.SECONDARY),
    ("optional", Importance.OPTIONAL),
)


class AgentRecipePresenter:
    """
    What: Flattens Recipe rows into the small JSON dictionaries the n8n agent
          reads back as tool output.
    Where: Used by AgentToolsUseCase for every tool that returns recipes.
    Why: The HTML presenters (FeaturedRecipePresenter, VectorMatchPresenter)
         decorate model instances with template-facing attributes — poster urls,
         thermometer hues, grouped ingredient dicts. None of that means anything
         to an LLM, and all of it costs context. This is the machine-readable
         counterpart: flat, named fields, hard length caps, JSON-safe types
         (Decimal amounts become floats, cuisine becomes a plain string).
    """

    @staticmethod
    def _cuisine(recipe) -> str:
        return recipe.cuisine.name if recipe.cuisine_id else "general"

    @classmethod
    def summary(cls, recipe, extra: dict = None) -> dict:
        """One line per recipe: enough for the model to choose, not to cook."""
        payload = {
            "id": recipe.id,
            "title": recipe.title,
            "cuisine": cls._cuisine(recipe),
            "cook_time_minutes": recipe.cook_time,
        }

        description = (recipe.description or "").strip()
        if description:
            payload["description"] = description[:MAX_DESCRIPTION_CHARS]

        # match_percent is the calibrated 0..100 figure the UI thermometer uses;
        # it is far more actionable for the model than a raw cosine distance,
        # which sits in a narrow band and reads as "everything is a 0.6 match".
        match_percent = getattr(recipe, "match_percent", None)
        if match_percent is not None:
            payload["match_percent"] = match_percent

        if extra:
            payload.update(extra)
        return payload

    @classmethod
    def summary_list(cls, recipes, extras: dict = None) -> list[dict]:
        extras = extras or {}
        return [cls.summary(recipe, extras.get(recipe.id)) for recipe in recipes]

    @classmethod
    def _ingredient(cls, recipe_ingredient) -> dict:
        return {
            "name": recipe_ingredient.ingredient.name,
            # Decimal is not JSON-serialisable, and the model reads "2" better than "2.00".
            "amount": float(recipe_ingredient.amount),
            "unit": recipe_ingredient.unit,
        }

    @classmethod
    def detail(cls, recipe, is_saved: bool = False) -> dict:
        """
        The full cooking payload: steps parsed out of the description plus the
        ingredients split by importance, so the agent can say what is optional.
        """
        recipe_ingredients = list(recipe.ingredients.all())[:MAX_INGREDIENTS]

        ingredients = {
            label: [
                cls._ingredient(ri) for ri in recipe_ingredients if ri.importance == importance
            ]
            for label, importance in IMPORTANCE_GROUPS
        }

        return {
            "id": recipe.id,
            "title": recipe.title,
            "cuisine": cls._cuisine(recipe),
            "cook_time_minutes": recipe.cook_time,
            "steps": RecipeStepsParser.parse(recipe.description)[:MAX_STEPS],
            "ingredients": ingredients,
            "is_saved": is_saved,
        }


class AgentGeneratedRecipePresenter:
    """
    What: The machine-readable form of a recipe the agent composed itself.
    Where: Returned by the `save_generated_recipe` tool once the recipe is stored.
    Why: Echoing back exactly what was written — normalised names, clamped
         amounts, the id it now has — lets the agent confirm to the user what was
         actually saved instead of repeating its own draft, which may differ.
    """

    @classmethod
    def detail(cls, generated) -> dict:
        lines = list(generated.ingredients.select_related("ingredient"))

        return {
            "id": generated.id,
            "title": generated.title,
            "cuisine": generated.cuisine or "general",
            "cook_time_minutes": generated.cook_time,
            "steps": generated.steps[:MAX_STEPS],
            "ingredients": {
                label: [
                    AgentRecipePresenter._ingredient(line)
                    for line in lines if line.importance == importance
                ]
                for label, importance in IMPORTANCE_GROUPS
            },
        }

    @classmethod
    def editable(cls, generated) -> dict:
        """
        The same flat shape SaveGeneratedRecipeUseCase.validate returns, built
        from a stored recipe instead of a proposal.

        The studio page speaks exactly one recipe shape — a fresh draft from the
        agent and an old creation loaded back from the database arrive in the
        editor identical, so the editor needs no idea where a recipe came from.
        """
        lines = list(generated.ingredients.select_related("ingredient"))

        return {
            "id": generated.id,
            "title": generated.title,
            "cuisine": generated.cuisine,
            "cook_time_minutes": generated.cook_time,
            # Empty until an image model fills it in; the editor and the preview
            # both read an empty one as "no photo".
            "image_url": generated.image_url,
            "steps": generated.steps[:MAX_STEPS],
            "ingredients": [
                {
                    "name": line.ingredient.name,
                    "amount": float(line.amount),
                    "unit": line.unit,
                    "importance": line.importance,
                }
                for line in lines
            ],
        }
