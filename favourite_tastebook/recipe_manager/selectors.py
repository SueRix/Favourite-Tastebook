from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Optional, Any

from django.db.models import Count, Q, F, Value, IntegerField, ExpressionWrapper, QuerySet
from django.http import QueryDict

from .models import Ingredient, RecipeIngredient, Recipe


@dataclass(frozen=True)
class RecipeScoreWeights:
    """Config for recipe scoring logic."""
    required_match: int = 10
    secondary_match: int = 4
    optional_match: int = 1
    missing_required_match: int = 12

    def get_score_expression(self) -> ExpressionWrapper:
        """Constructs DB-level calculation for ranking recipes."""
        score_calc = (
            F("required_matched") * Value(self.required_match)
            + F("secondary_matched") * Value(self.secondary_match)
            + F("optional_matched") * Value(self.optional_match)
            - (F("required_total") - F("required_matched")) * Value(self.missing_required_match)
        )
        return ExpressionWrapper(score_calc, output_field=IntegerField())


def get_ingredient_categories() -> QuerySet:
    return (
        Ingredient.objects
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )


def get_ingredients(
    q: Optional[str] = None,
    category: Optional[str] = None,
) -> QuerySet:
    qs = Ingredient.objects.all()

    if q := (q or "").strip():
        qs = qs.filter(name__icontains=q)

    if category := (category or "").strip():
        qs = qs.filter(category=category)

    return qs.order_by("category", "name")


def clean_int_ids(values: Iterable[Any]) -> list[int]:
    """Safe integer parsing from mixed input. Deduplicates preserving order."""
    parsed: list[int] = []

    for v in values:
        try:
            if v in (None, ""):
                continue
            parsed.append(int(v))
        except (ValueError, TypeError):
            continue

    return list(dict.fromkeys(parsed))


def extract_ingredient_ids(query_params: QueryDict) -> list[int]:
    """Parses IDs from both CSV strings and list params."""
    parts: list[Any] = []

    # Handle ?ingredients=1,2,3
    csv = (query_params.get("ingredients") or "").strip()
    if csv:
        parts.extend(csv.split(","))

    # Handle ?ingredient=1&ingredient=2
    parts.extend(query_params.getlist("ingredient"))

    return clean_int_ids(parts)


def _count_by_importance(
    importance: str,
    selected_ids: Optional[Sequence[int]] = None,
) -> Count:
    """Builds conditional count for annotation."""
    filters = Q(ingredients__importance=importance)

    if selected_ids:
        filters &= Q(ingredients__ingredient_id__in=selected_ids)

    return Count("ingredients", filter=filters, distinct=True)


def search_recipes_by_ingredients(
        selected_ids: Sequence[int],
        strict_required: bool,
        weights: Optional[RecipeScoreWeights] = None,
) -> QuerySet:
    if not selected_ids:
        return Recipe.objects.none()

    config = weights or RecipeScoreWeights()

    aggregates = {
        "required_total": _count_by_importance(RecipeIngredient.Importance.REQUIRED),
        "required_matched": _count_by_importance(RecipeIngredient.Importance.REQUIRED, selected_ids),
        "secondary_matched": _count_by_importance(RecipeIngredient.Importance.SECONDARY, selected_ids),
        "optional_matched": _count_by_importance(RecipeIngredient.Importance.OPTIONAL, selected_ids),
    }

    qs = (
        Recipe.objects
        .select_related("cuisine")
        .prefetch_related("ingredients__ingredient")
        .annotate(**aggregates)
        .annotate(
            total_matches=F("required_matched") + F("secondary_matched") + F("optional_matched"),

            missing_required=ExpressionWrapper(
                F("required_total") - F("required_matched"),
                output_field=IntegerField(),
            ),
            score=config.get_score_expression(),
        )
    )

    if strict_required:
        qs = qs.filter(missing_required=0)
    else:
        qs = qs.filter(total_matches__gt=0)

    return qs.order_by(
        "-score",
        "missing_required",
        "-required_matched",
        "cook_time",
        "title",
    )