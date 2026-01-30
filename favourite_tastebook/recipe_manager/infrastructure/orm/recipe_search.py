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
        qs = RecipeScoringService.annotate_scores(qs, selected_ids)

        if strict:
            qs = qs.filter(missing_required=0)
        else:
            qs = qs.filter(total_matches__gt=0)

        return qs.order_by("-score", "missing_required", "title")