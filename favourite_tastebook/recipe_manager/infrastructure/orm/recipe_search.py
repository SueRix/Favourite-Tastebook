from django.db.models import Prefetch
from recipe_manager.models import Recipe, RecipeIngredient
from recipe_manager.infrastructure.orm.scoring import RecipeScoringService
from recipe_manager.infrastructure.selectors.ingredients import IngredientSelector

class RecipeSearchORM:
    @classmethod
    def find_recipes(cls, filters: dict):
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

        qs = RecipeScoringService.annotate_base_metrics(qs, selected_ids)

        strict_val = filters.get("strict")
        if isinstance(strict_val, list):
            strict_val = strict_val[0] if strict_val else ""

        is_strict_mode = str(strict_val) == "1"

        print(f"--- DEBUG SEARCH ---")
        print(f"AI Mode: {is_ai_mode} | Strict Mode: {is_strict_mode} | Selected IDs: {len(selected_ids)}")

        if is_strict_mode:
            print("----> STRICT SCORING IS RUNNING <----")
            qs = RecipeScoringService.apply_strict_scoring(qs)
            qs = qs.exclude(relevance_tier=3)
        elif is_ai_mode:
            print("----> AI SCORING IS RUNNING <----")
            qs = RecipeScoringService.apply_ai_scoring(qs)
            qs = qs.exclude(relevance_tier=3)
        else:
            print("----> NORMAL SCORING IS RUNNING <----")
            qs = RecipeScoringService.apply_normal_scoring(qs)
            qs = qs.exclude(relevance_tier=3)

        return qs.order_by("relevance_tier", "-score", "missing_required", "missing_secondary", "title")