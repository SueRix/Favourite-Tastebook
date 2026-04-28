from django.db.models import Prefetch

from recipe_manager.domain.enums import TASTE_HATE_LEVEL
from recipe_manager.models import Recipe, RecipeIngredient, UserTastePreference
from recipe_manager.infrastructure.orm.scoring import RecipeScoringService
from recipe_manager.infrastructure.selectors.ingredients import IngredientSelector

class RecipeSearchORM:
    @classmethod
    def find_recipes(cls, filters: dict, user=None):
        is_ai_mode = IngredientSelector.is_ai_mode(filters)

        selected_ingredients_qs = IngredientSelector.list_selected(filters)
        selected_ids = list(selected_ingredients_qs.values_list("id", flat=True))

        if not selected_ids:
            return Recipe.objects.none()

        qs = (
            Recipe.objects
            .select_related("cuisine")
            .prefetch_related(
                Prefetch(
                    "ingredients",
                    queryset=(
                        RecipeIngredient.objects
                        .select_related("ingredient")
                        .order_by("importance", "ingredient__name")
                    ),
                )
            )
        )

        #hard filter for user's hated ingredient in recipes.
        if user and user.is_authenticated:
            hated_ids = UserTastePreference.objects.filter(
                user=user,
                score=TASTE_HATE_LEVEL
            ).values_list('ingredient_id', flat=True)

            if hated_ids.exists():
                qs = qs.exclude(ingredients__ingredient_id__in=hated_ids)

        qs = RecipeScoringService.annotate_base_metrics(qs, selected_ids)

        is_strict_mode = filters.get("strict") == "1"

        if is_strict_mode:
            qs = RecipeScoringService.apply_strict_scoring(qs)
            qs = qs.exclude(relevance_tier=3)
        elif is_ai_mode:
            qs = RecipeScoringService.apply_ai_scoring(qs)
            qs = qs.exclude(relevance_tier=3)
        else:
            qs = RecipeScoringService.apply_normal_scoring(qs)
            qs = qs.exclude(relevance_tier=3)

        return qs.order_by("relevance_tier", "-score", "missing_required", "missing_secondary", "title")