from django.db.models import Prefetch
from recipe_manager.models import Recipe, RecipeIngredient
from recipe_manager.infrastructure.orm.scoring import RecipeScoringService
from recipe_manager.infrastructure.selectors.ingredients import IngredientSelector

class RecipeSearchORM:
    @classmethod
    def find_recipes(cls, filters: dict):
        is_ai_mode = False
        if hasattr(filters, "getlist"):
            is_ai_mode = bool(filters.getlist("ai_selected"))
        elif "ai_selected" in filters:
            is_ai_mode = bool(filters.get("ai_selected"))

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

        qs = RecipeScoringService.annotate_base_metrics(qs, selected_ids)

        if is_ai_mode:
            qs = RecipeScoringService.apply_ai_scoring(qs)
            qs = qs.exclude(relevance_tier=3)
        elif filters.get("strict", False):
            qs = RecipeScoringService.apply_strict_scoring(qs)
            qs = qs.exclude(relevance_tier=3)
        else:
            qs = RecipeScoringService.apply_normal_scoring(qs)
            qs = qs.exclude(relevance_tier=3)

        return qs.order_by("relevance_tier", "-score", "missing_required", "missing_secondary", "title")