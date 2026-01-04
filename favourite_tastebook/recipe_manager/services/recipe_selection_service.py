from django.db.models import Count, Q, F, Value, IntegerField, ExpressionWrapper
from django.db.models.query import QuerySet

from recipe_manager.domain.constants import (
    SCORE_REQUIRED_MATCH,
    SCORE_SECONDARY_MATCH,
    SCORE_OPTIONAL_MATCH,
    SCORE_MISSING_REQUIRED_PENALTY,
)
from recipe_manager.domain.enums import Importance


def count_total(importance):
    q = Q(ingredients__importance=importance)
    return Count("ingredients", filter=q, distinct=True)


def count_matched(importance, selected_ids: list[int]):
    q = Q(ingredients__importance=importance, ingredients__ingredient_id__in=selected_ids)
    return Count("ingredients", filter=q, distinct=True)


def annotate_recipe_scores(*, qs: QuerySet, selected_ids: list[int], weights: dict | None = None) -> QuerySet:
    w = {
        "required_match": SCORE_REQUIRED_MATCH,
        "secondary_match": SCORE_SECONDARY_MATCH,
        "optional_match": SCORE_OPTIONAL_MATCH,
        "missing_required_match": SCORE_MISSING_REQUIRED_PENALTY,
    }
    if weights:
        w.update(weights)

    required = Importance.REQUIRED
    secondary = Importance.SECONDARY
    optional = Importance.OPTIONAL

    return (
        qs.annotate(
            required_total=count_total(required),
            required_matched=count_matched(required, selected_ids),
            secondary_matched=count_matched(secondary, selected_ids),
            optional_matched=count_matched(optional, selected_ids),
        )
        .annotate(
            total_matches=F("required_matched") + F("secondary_matched") + F("optional_matched"),
            missing_required=F("required_total") - F("required_matched"),
        )
        .annotate(
            score=ExpressionWrapper(
                F("required_matched") * Value(w["required_match"])
                + F("secondary_matched") * Value(w["secondary_match"])
                + F("optional_matched") * Value(w["optional_match"])
                - F("missing_required") * Value(w["missing_required_match"]),
                output_field=IntegerField(),
            ),
        )
    )