from django.db.models import Count, Q, F, Value, IntegerField, ExpressionWrapper
from recipe_manager.domain.enums import Importance
from recipe_manager.domain.enums import (
    SCORE_REQUIRED_MATCH,
    SCORE_SECONDARY_MATCH,
    SCORE_OPTIONAL_MATCH,
    SCORE_MISSING_REQUIRED_PENALTY,
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
        }
        if weights:
            w.update(weights)

        req, sec, opt = Importance.REQUIRED, Importance.SECONDARY, Importance.OPTIONAL

        return (
            qs.annotate(
                required_total=cls.count_total(req),
                required_matched=cls.count_matched(req, selected_ids),
                secondary_matched=cls.count_matched(sec, selected_ids),
                optional_matched=cls.count_matched(opt, selected_ids),
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