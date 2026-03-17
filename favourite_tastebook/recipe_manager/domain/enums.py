from django.db import models


class Units(models.TextChoices):
    GRAM = "g", "g"
    KILOGRAM = "kg", "kg"
    LITER = "l", "l"
    PIECE = "pcs", "pcs"
    TABLESPOON = "tbsp", "tbsp"
    TEASPOON = "tsp", "tsp"
    PINCH = "pinch", "pinch"


class Importance(models.TextChoices):
    REQUIRED = "required", "required"
    SECONDARY = "secondary", "secondary"
    OPTIONAL = "optional", "optional"


# Importance values stored in DB
IMPORTANCE_REQUIRED = "required"
IMPORTANCE_SECONDARY = "secondary"
IMPORTANCE_OPTIONAL = "optional"


# Default scoring weights (used in selectors/services)
SCORE_REQUIRED_MATCH = 10
SCORE_SECONDARY_MATCH = 4
SCORE_OPTIONAL_MATCH = 1
SCORE_MISSING_REQUIRED_PENALTY = 6
SCORE_MISSING_SECONDARY_PENALTY = 2

# AI scoring weights and thresholds
SCORE_AI_MISSING_REQUIRED_PENALTY = 2
SCORE_AI_MISSING_SECONDARY_PENALTY = 0
SCORE_AI_DENSITY_BONUS = 2

AI_TIER_1_MIN_SCORE = 0
AI_TIER_1_MIN_MATCHES = 2
AI_TIER_2_MIN_MATCHES = 1