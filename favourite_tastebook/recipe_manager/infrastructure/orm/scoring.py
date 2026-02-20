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
    def annotate_base_metrics(cls, qs, selected_ids):
        req = Importance.REQUIRED
        sec = Importance.SECONDARY
        opt = Importance.OPTIONAL

        return (
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
        )

    @classmethod
    def apply_normal_scoring(cls, qs):
        w_req = SCORE_REQUIRED_MATCH
        w_sec = SCORE_SECONDARY_MATCH
        w_opt = SCORE_OPTIONAL_MATCH

        qs = qs.annotate(
            score=ExpressionWrapper(
                F("required_matched") * Value(w_req)
                + F("secondary_matched") * Value(w_sec)
                + F("optional_matched") * Value(w_opt),
                output_field=IntegerField(),
            )
        )

        qs = qs.annotate(
            relevance_tier=Case(
                When(required_matched__gte=1, then=Value(1)),
                When(total_matches__gte=1, then=Value(2)),
                default=Value(3),
                output_field=IntegerField()
            )
        )
        return qs

    @classmethod
    def apply_strict_scoring(cls, qs):
        w_req = SCORE_REQUIRED_MATCH
        w_sec = SCORE_SECONDARY_MATCH
        w_opt = SCORE_OPTIONAL_MATCH
        w_miss_req = SCORE_MISSING_REQUIRED_PENALTY
        w_miss_sec = SCORE_MISSING_SECONDARY_PENALTY

        qs = qs.annotate(
            score=ExpressionWrapper(
                F("required_matched") * Value(w_req)
                + F("secondary_matched") * Value(w_sec)
                + F("optional_matched") * Value(w_opt)
                - F("missing_required") * Value(w_miss_req)
                - F("missing_secondary") * Value(w_miss_sec),
                output_field=IntegerField(),
            )
        )

        qs = qs.annotate(
            relevance_tier=Case(
                When(
                    Q(score__gte=0) & Q(required_matched__gte=1),
                    then=Value(1)
                ),
                When(
                    Q(total_matches__gte=1) & Q(score__gte=-15),
                    then=Value(2)
                ),
                default=Value(3),
                output_field=IntegerField()
            )
        )
        return qs