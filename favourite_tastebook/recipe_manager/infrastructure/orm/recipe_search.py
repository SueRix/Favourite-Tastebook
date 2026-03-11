from django.db.models import Prefetch

from recipe_manager.models import Recipe, RecipeIngredient
from recipe_manager.infrastructure.orm.scoring import RecipeScoringService


class RecipeSearchORM:
    @classmethod
    def find_recipes(cls, filters: dict):
        selected_ingredients = filters.get("ingredient")
        strict = filters.get("strict", False)

        if not selected_ingredients:
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

        selected_ids = list(selected_ingredients.values_list("id", flat=True))

        qs = RecipeScoringService.annotate_base_metrics(qs, selected_ids)

        if strict:
            qs = RecipeScoringService.apply_strict_scoring(qs)
            qs = qs.exclude(relevance_tier=3)
        else:
            qs = RecipeScoringService.apply_normal_scoring(qs)
            qs = qs.exclude(relevance_tier=3)

        return qs.order_by("relevance_tier", "-score", "missing_required", "missing_secondary", "title")