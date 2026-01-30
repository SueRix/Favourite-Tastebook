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
SCORE_MISSING_REQUIRED_PENALTY = 12
