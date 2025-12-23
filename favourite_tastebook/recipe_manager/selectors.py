from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db.models import (Count, Q, F, Value, IntegerField, ExpressionWrapper)
from django.db.models.functions import Coalesce

from .models import Ingredient, RecipeIngredient, Recipe

@dataclass(frozen=True)
class RecipeScoreWeights:
    required_match: int = 10
    secondary_match: int = 4
    optional_match: int = 1
    missing_required_match: int = 12

def get_ingredient_categories():
    return Ingredient.objects.values_list('category', flat=True).distinct().order_by('category')

def get_ingredients(*, q: str | None = None, category: str | None = None):
    qs = Ingredient.objects.all()

    if q:
        qs = qs.filter(name__icontains=q.strip().lower())

    if category:
        qs = qs.filter(category=category)

    return qs.order_by('category','name')

def _clean_int_ids(values: Iterable[int]) -> list[int]:
    out: list[int] = []
    for v in values:
        v = (v or "").strip()
        if not v:
            continue
        try:
            out.append(int(v))
        except ValueError:
            continue
    seen = set()
    deduped = []
    for x in out:
        if x not in seen:
            seen.add(x)
            deduped.append(x)
    return deduped

def parse_selected_ingredient_ids(querydict) -> list[int]:
    raw_csv = querydict.get("ingredients", "")
    raw_list = querydict.getlist("ingredient")

    ids = []
    if raw_csv:
        ids.extend(raw_csv.split(","))
    if raw_list:
        ids.extend(raw_list)

    return _clean_int_ids(ids)


def search_recipes_by_ingredients(
    *,
    selected_ids: list[int],
    strict_required: bool,
    weights: RecipeScoreWeights = RecipeScoreWeights(),
):
    if not selected_ids:
        return Recipe.objects.none()

    required_total = Coalesce(
        Count(
            "ingredients",
            filter=Q(ingredients__importance=RecipeIngredient.Importance.REQUIRED),
            distinct=True,
        ),
        0,
    )
    required_matched = Coalesce(
        Count(
            "ingredients",
            filter=Q(
                ingredients__importance=RecipeIngredient.Importance.REQUIRED,
                ingredients__ingredient_id__in=selected_ids,
            ),
            distinct=True,
        ),
        0,
    )
    secondary_matched = Coalesce(
        Count(
            "ingredients",
            filter=Q(
                ingredients__importance=RecipeIngredient.Importance.SECONDARY,
                ingredients__ingredient_id__in=selected_ids,
            ),
            distinct=True,
        ),
        0,
    )
    optional_matched = Coalesce(
        Count(
            "ingredients",
            filter=Q(
                ingredients__importance=RecipeIngredient.Importance.OPTIONAL,
                ingredients__ingredient_id__in=selected_ids,
            ),
            distinct=True,
        ),
        0,
    )

    qs = (
        Recipe.objects
        .select_related("cuisine")
        .prefetch_related("ingredients__ingredient")
        .annotate(
            required_total=required_total,
            required_matched=required_matched,
            secondary_matched=secondary_matched,
            optional_matched=optional_matched,
        )
        .annotate(
            missing_required=ExpressionWrapper(
                F("required_total") - F("required_matched"),
                output_field=IntegerField(),
            ),
        )
        .annotate(
            score=ExpressionWrapper(
                F("required_matched") * Value(weights.required_match)
                + F("secondary_matched") * Value(weights.secondary_match)
                + F("optional_matched") * Value(weights.optional_match)
                - F("missing_required") * Value(weights.missing_required_match),
                output_field=IntegerField(),
            )
        )
    )

    if strict_required:
        qs = qs.filter(missing_required=0)

    return qs.order_by(
        "-score",
        "missing_required",
        "-required_matched",
        "-secondary_matched",
        "-optional_matched",
        "cook_time",
        "title",
    )