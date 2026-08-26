from django.db.models import Count, Q, F, Value, IntegerField, ExpressionWrapper, Case, When
from recipe_manager.domain.enums import Importance
from recipe_manager.domain.enums import (
    SCORE_REQUIRED_MATCH,
    SCORE_SECONDARY_MATCH,
    SCORE_OPTIONAL_MATCH,
    SCORE_MISSING_REQUIRED_PENALTY,
    SCORE_MISSING_SECONDARY_PENALTY,
    SCORE_AI_MISSING_REQUIRED_PENALTY,
    SCORE_AI_MISSING_SECONDARY_PENALTY,
    SCORE_AI_DENSITY_BONUS,
    AI_TIER_1_MIN_SCORE,
    AI_TIER_1_MIN_MATCHES,
    AI_TIER_2_MIN_MATCHES,
)
from recipe_manager.domain.exceptions.selectors import EmptyQueryValueError
from recipe_manager.domain.exceptions.services import (
    EmptyIngredientsError,
    InvalidWeightConfigurationError,
)

class RecipeScoringService:
    DEFAULT_WEIGHTS = {
        "required_match": SCORE_REQUIRED_MATCH,
        "secondary_match": SCORE_SECONDARY_MATCH,
        "optional_match": SCORE_OPTIONAL_MATCH,
        "missing_required_match": SCORE_MISSING_REQUIRED_PENALTY,
        "missing_secondary_match": SCORE_MISSING_SECONDARY_PENALTY,
    }

    @staticmethod
    def validate_selected_ids(selected_ids):
        """
        What: Guards the raw ingredient-id list before it reaches the ORM.
        Why: A None/non-list/empty-valued input silently produced a bogus queryset
             before; callers now get a clear domain error instead.
        """
        if selected_ids is None or not isinstance(selected_ids, (list, tuple, set)):
            raise EmptyQueryValueError("selected_ids must be a list of ingredient ids.")
        if any(not sid for sid in selected_ids):
            raise EmptyQueryValueError("selected_ids must not contain empty values.")
        if not selected_ids:
            raise EmptyIngredientsError("At least one ingredient id is required.")

    @classmethod
    def _resolve_weights(cls, weights):
        if not weights:
            return dict(cls.DEFAULT_WEIGHTS)

        unknown = set(weights) - set(cls.DEFAULT_WEIGHTS)
        if unknown:
            raise InvalidWeightConfigurationError(f"Unknown weight keys: {sorted(unknown)}")

        merged = dict(cls.DEFAULT_WEIGHTS)
        merged.update(weights)
        return merged

    @classmethod
    def annotate_recipe_scores(cls, qs, selected_ids, weights=None):
        """
        What: Validated, configurable-weight scoring pass over a recipe queryset.
        Where: Used directly (tests, ad-hoc scoring) when the caller already has raw
               selected_ids rather than going through RecipeSearchORM.find_recipes.
        """
        cls.validate_selected_ids(selected_ids)
        resolved = cls._resolve_weights(weights)

        qs = cls.annotate_base_metrics(qs, selected_ids)
        return qs.annotate(
            score=cls._build_score_expression(
                w_req=resolved["required_match"],
                w_sec=resolved["secondary_match"],
                w_opt=resolved["optional_match"],
                w_miss_req=resolved["missing_required_match"],
                w_miss_sec=resolved["missing_secondary_match"],
            )
        )

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
                optional_total=cls.count_total(opt),
                required_matched=cls.count_matched(req, selected_ids),
                secondary_matched=cls.count_matched(sec, selected_ids),
                optional_matched=cls.count_matched(opt, selected_ids),
            )
            .annotate(
                total_matches=F("required_matched") + F("secondary_matched") + F("optional_matched"),
                missing_required=F("required_total") - F("required_matched"),
                missing_secondary=F("secondary_total") - F("secondary_matched"),
                max_score=ExpressionWrapper(
                    F("required_total") * Value(SCORE_REQUIRED_MATCH)
                    + F("secondary_total") * Value(SCORE_SECONDARY_MATCH)
                    + F("optional_total") * Value(SCORE_OPTIONAL_MATCH),
                    output_field=IntegerField(),
                ),
            )
        )

    @staticmethod
    def _build_score_expression(w_req, w_sec, w_opt, w_miss_req=0, w_miss_sec=0):
        """
        Builds the Django ORM ExpressionWrapper for score calculation.
        Reusable component for normal, strict, and AI scoring methods.
        """
        return ExpressionWrapper(
            F("required_matched") * Value(w_req)
            + F("secondary_matched") * Value(w_sec)
            + F("optional_matched") * Value(w_opt)
            - F("missing_required") * Value(w_miss_req)
            - F("missing_secondary") * Value(w_miss_sec),
            output_field=IntegerField(),
        )

    @classmethod
    def apply_normal_scoring(cls, qs):
        qs = qs.annotate(
            score=cls._build_score_expression(
                w_req=SCORE_REQUIRED_MATCH,
                w_sec=SCORE_SECONDARY_MATCH,
                w_opt=SCORE_OPTIONAL_MATCH
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
        qs = qs.annotate(
            score=cls._build_score_expression(
                w_req=SCORE_REQUIRED_MATCH,
                w_sec=SCORE_SECONDARY_MATCH,
                w_opt=SCORE_OPTIONAL_MATCH,
                w_miss_req=SCORE_MISSING_REQUIRED_PENALTY,
                w_miss_sec=SCORE_MISSING_SECONDARY_PENALTY
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

    @classmethod
    def apply_ai_scoring(cls, qs):
        qs = qs.annotate(
            base_score=cls._build_score_expression(
                w_req=SCORE_REQUIRED_MATCH,
                w_sec=SCORE_SECONDARY_MATCH,
                w_opt=SCORE_OPTIONAL_MATCH,
                w_miss_req=SCORE_AI_MISSING_REQUIRED_PENALTY,
                w_miss_sec=SCORE_AI_MISSING_SECONDARY_PENALTY
            ),
            score=ExpressionWrapper(
                F("base_score") + (F("total_matches") * Value(SCORE_AI_DENSITY_BONUS)),
                output_field=IntegerField()
            )
        )

        qs = qs.annotate(
            relevance_tier=Case(
                When(
                    Q(score__gte=AI_TIER_1_MIN_SCORE) & Q(total_matches__gte=AI_TIER_1_MIN_MATCHES),
                    then=Value(1)
                ),
                When(
                    Q(total_matches__gte=AI_TIER_2_MIN_MATCHES),
                    then=Value(2)
                ),
                default=Value(3),
                output_field=IntegerField()
            )
        )
        return qs