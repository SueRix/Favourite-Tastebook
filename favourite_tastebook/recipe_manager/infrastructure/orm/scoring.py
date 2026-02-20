from django.db.models import Count, Q, F, Value, IntegerField, ExpressionWrapper, Case, When
from recipe_manager.domain.enums import Importance
from recipe_manager.domain.enums import (
    SCORE_REQUIRED_MATCH,
    SCORE_SECONDARY_MATCH,
    SCORE_OPTIONAL_MATCH,
    SCORE_MISSING_REQUIRED_PENALTY,
    SCORE_MISSING_SECONDARY_PENALTY,
)

class RecipeScoringService:
    @staticmethod
    def count_total(importance):
        q = Q(ingredients__importance=importance)
        return Count("ingredients", filter=q, distinct=True)

    @staticmethod
    def count_matched(importance, selected_ids):
        q = Q(ingredients__importance=importance, ingredients__ingredient_id__in=selected_ids)
        return Count("ingredients", filter=q, distinct=True)

    @classmethod
    def annotate_scores(cls, qs, selected_ids, weights=None):
        w = {
            "required_match": SCORE_REQUIRED_MATCH,
            "secondary_match": SCORE_SECONDARY_MATCH,
            "optional_match": SCORE_OPTIONAL_MATCH,
            "missing_required_match": SCORE_MISSING_REQUIRED_PENALTY,
            "missing_secondary_match": SCORE_MISSING_SECONDARY_PENALTY,
        }
        if weights:
            w.update(weights)

        req = Importance.REQUIRED
        sec = Importance.SECONDARY
        opt = Importance.OPTIONAL

        qs = (
            qs.annotate(
                required_total=cls.count_total(req),
                secondary_total=cls.count_total(sec),
                required_matched=cls.count_matched(req, selected_ids),
                secondary_matched=cls.count_matched(sec, selected_ids),
                optional_matched=cls.count_matched(opt, selected_ids),
            )
            .annotate(
                total_matches=F("required_matched") + F("secondary_matched") + F("optional_matched"),
                missing_required=F("required_total") - F("required_matched"),
                missing_secondary=F("secondary_total") - F("secondary_matched"),
            )
            .annotate(
                score=ExpressionWrapper(
                    F("required_matched") * Value(w["required_match"])
                    + F("secondary_matched") * Value(w["secondary_match"])
                    + F("optional_matched") * Value(w["optional_match"])
                    - F("missing_required") * Value(w["missing_required_match"])
                    - F("missing_secondary") * Value(w["missing_secondary_match"]),
                    output_field=IntegerField(),
                )
            )
        )

        qs = qs.annotate(
            relevance_tier=Case(
                # Tier 1: At least one required and total matches >= 2
                When(
                    Q(required_matched__gte=1) & Q(total_matches__gte=2),
                    then=Value(1)
                ),
                # Tier 2: Positive score and at least one match, but doesn't fit Tier 1
                When(
                    Q(score__gt=0) & Q(total_matches__gte=1),
                    then=Value(2)
                ),
                # Tier 3: Garbage (no required ingredients, negative score, etc.)
                default=Value(3),
                output_field=IntegerField()
            )
        )

        return qs