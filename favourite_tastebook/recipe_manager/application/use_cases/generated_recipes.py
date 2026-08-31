from django.db import IntegrityError, transaction

from recipe_manager.domain.enums import Importance, TASTE_HATE_LEVEL, Units
from recipe_manager.domain.exceptions import (
    GeneratedRecipeAlreadySavedError,
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
    What: Turns a recipe the agent invented into rows the app owns.
    Where: Called by AgentToolsUseCase.save_generated_recipe.
    Why: This is the only place where text produced by a language model becomes
         persistent data, so it is also the only place where that text can be
         checked. Two guarantees are enforced here and nowhere else: every
         ingredient is one we already know, and none of them is on the user's
         never_use list. The system prompt asks for both; a prompt is advice,
         and this is the check that actually holds.
    """

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

    @classmethod
    def execute(cls, user, *, title: str, cook_time: int, steps: list[str],
                ingredient_lines: list[dict], cuisine: str = "",
                session_id: str = "") -> GeneratedRecipe:
        """
        `ingredient_lines` are dicts of {name, amount, unit, importance}, already
        type-checked by AgentInput. Returns the stored recipe.
        """
        resolved = cls._resolve_ingredients(ingredient_lines)
        cls._reject_taboo(user, [ingredient for ingredient, _ in resolved])

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
                    # A model listing the same ingredient twice would break the
                    # unique constraint mid-transaction; keep the first line.
                    for ingredient, line in cls._deduplicate(resolved)
                )
        except IntegrityError as exc:
            # (user, title) is the only other unique constraint in play.
            raise GeneratedRecipeAlreadySavedError() from exc

        return recipe

    @staticmethod
    def _deduplicate(resolved: list[tuple]) -> list[tuple]:
        seen = set()
        unique = []
        for ingredient, line in resolved:
            if ingredient.id in seen:
                continue
            seen.add(ingredient.id)
            unique.append((ingredient, line))
        return unique
