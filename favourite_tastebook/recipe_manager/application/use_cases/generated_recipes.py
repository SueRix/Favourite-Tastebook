from django.db import IntegrityError, transaction

from recipe_manager.domain.enums import Importance, TASTE_HATE_LEVEL, Units
from recipe_manager.domain.exceptions import (
    GeneratedRecipeAlreadySavedError,
    GeneratedRecipeNotFoundError,
    TabooIngredientError,
    UnknownIngredientsError,
)
from recipe_manager.infrastructure.selectors import IngredientSelector
from recipe_manager.models import (
    GeneratedRecipe,
    GeneratedRecipeIngredient,
    UserTastePreference,
)

# Bounds for a dish description, independent of what the model proposes.
MIN_COOK_TIME = 1
MAX_COOK_TIME = 1440


class SaveGeneratedRecipeUseCase:
    """
    What: Turns a recipe the agent composed into rows the app owns — and, one
          step earlier, tells the caller whether it could be turned into rows
          at all.
    Where: `validate` backs the `propose_recipe` tool and the studio preview;
           `execute` backs both save paths (the agent's tool and the button on
           the studio page).
    Why: This is the only place where text produced by a language model becomes
         persistent data, so it is also the only place where that text can be
         checked. Two guarantees live here and nowhere else: every ingredient is
         one we already know, and none of them is on the user's never_use list.
         The system prompt asks for both; a prompt is advice, and this is the
         check that actually holds.

    `validate` and `execute` run the same checks in the same order on purpose.
    The studio page shows a draft the user may edit before keeping it, so a draft
    that validated must not become a save that fails on something different.
    """

    # ---------------------------------------------------------------- checks

    @classmethod
    def _resolve_ingredients(cls, lines: list[dict]) -> list[tuple]:
        """
        Pairs each requested line with a catalogue row. Raises with the full list
        of unknown names rather than the first one: the agent should be able to
        fix the whole recipe in one retry.
        """
        names = [line["name"] for line in lines]
        found = IngredientSelector.resolve_names(names)

        unknown = [name for name in names if name not in found]
        if unknown:
            raise UnknownIngredientsError(unknown)

        return [(found[line["name"]], line) for line in lines]

    @classmethod
    def _reject_taboo(cls, user, ingredients) -> None:
        taboo = set(
            UserTastePreference.objects
            .filter(user=user, score=TASTE_HATE_LEVEL, ingredient__in=ingredients)
            .values_list("ingredient__name", flat=True)
        )
        if taboo:
            raise TabooIngredientError(sorted(taboo))

    @staticmethod
    def _deduplicate(resolved: list[tuple]) -> list[tuple]:
        # A model listing the same ingredient twice would break the unique
        # constraint mid-transaction; keep the first line it gave.
        seen = set()
        unique = []
        for ingredient, line in resolved:
            if ingredient.id in seen:
                continue
            seen.add(ingredient.id)
            unique.append((ingredient, line))
        return unique

    @classmethod
    def _checked_lines(cls, user, ingredient_lines: list[dict]) -> list[tuple]:
        resolved = cls._resolve_ingredients(ingredient_lines)
        cls._reject_taboo(user, [ingredient for ingredient, _ in resolved])
        return cls._deduplicate(resolved)

    # ------------------------------------------------------------ operations

    @classmethod
    def validate(cls, user, *, title: str, cook_time: int, steps: list[str],
                 ingredient_lines: list[dict], cuisine: str = "") -> dict:
        """
        Runs every check and returns the recipe in the form it WOULD be stored
        in, without storing it. Nothing is written, so the agent can propose
        freely and the person decides afterwards.

        The shape is deliberately flat rather than grouped by importance: this
        one is going into an editor, where every line needs its own row.
        """
        checked = cls._checked_lines(user, ingredient_lines)

        return {
            "title": title,
            "cuisine": cuisine,
            "cook_time_minutes": min(max(int(cook_time), MIN_COOK_TIME), MAX_COOK_TIME),
            "steps": steps,
            "ingredients": [
                {
                    "name": ingredient.name,
                    # Decimal is not JSON-serialisable, and a person reads "2"
                    # more easily than "2.00".
                    "amount": float(line["amount"]),
                    "unit": line.get("unit") or Units.GRAM,
                    "importance": line.get("importance") or Importance.REQUIRED,
                }
                for ingredient, line in checked
            ],
        }

    @classmethod
    def execute(cls, user, *, title: str, cook_time: int, steps: list[str],
                ingredient_lines: list[dict], cuisine: str = "",
                session_id: str = "") -> GeneratedRecipe:
        """
        `ingredient_lines` are dicts of {name, amount, unit, importance}, already
        type-checked by GeneratedRecipeInput. Returns the stored recipe.
        """
        checked = cls._checked_lines(user, ingredient_lines)
        cook_time = min(max(int(cook_time), MIN_COOK_TIME), MAX_COOK_TIME)

        try:
            with transaction.atomic():
                recipe = GeneratedRecipe.objects.create(
                    user=user,
                    title=title,
                    cuisine=cuisine,
                    cook_time=cook_time,
                    steps=steps,
                    session_id=session_id,
                )
                GeneratedRecipeIngredient.objects.bulk_create(
                    GeneratedRecipeIngredient(
                        generated_recipe=recipe,
                        ingredient=ingredient,
                        amount=line["amount"],
                        unit=line.get("unit") or Units.GRAM,
                        importance=line.get("importance") or Importance.REQUIRED,
                    )
                    for ingredient, line in checked
                )
        except IntegrityError as exc:
            # (user, title) is the only other unique constraint in play.
            raise GeneratedRecipeAlreadySavedError() from exc

        return recipe


class DeleteGeneratedRecipeUseCase:
    """
    What: Removes one of the user's own creations.
    Where: Called by the studio page; there is no agent tool for it on purpose.
    Why: Saving is something the agent may do for you — it is additive, and a
         recipe too many costs nothing. Deleting is not: it is the one operation
         no misread instruction should be able to perform, so it stays a button
         a person presses.

    Ownership is part of the query rather than a check after it. A creation that
    belongs to somebody else must be indistinguishable from one that never
    existed, or the endpoint becomes a way to probe for ids.
    """

    @classmethod
    def execute(cls, user, recipe_id: int) -> str:
        """Returns the title of the deleted recipe, for the message the user reads."""
        recipe = GeneratedRecipe.objects.filter(user=user, id=recipe_id).first()
        if recipe is None:
            raise GeneratedRecipeNotFoundError(recipe_id)

        title = recipe.title
        # The ingredient lines cascade with it; the Ingredient rows they point at
        # are shared catalogue data and stay.
        recipe.delete()
        return title
