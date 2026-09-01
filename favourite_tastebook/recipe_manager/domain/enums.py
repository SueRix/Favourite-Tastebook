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


class TasteLevels(models.IntegerChoices):
    HATE = -2, "Hate"
    DISLIKE = -1, "Do not like"
    NEUTRAL = 0, "Indifferent"
    LIKE = 1, "Like"
    LOVE = 2, "Love"

#const tabu filter
TASTE_HATE_LEVEL = -2


class AgentRecipeSource(models.TextChoices):
    """
    Where the cooking agent is allowed to look for a dish.

    Not a boolean, because the two values are not "on" and "off" of the same
    thing: DATABASE means the curated catalogue somebody wrote and photographed,
    AI means the model composing out of its own knowledge. Naming both keeps the
    setting readable in the admin and leaves room for a third source later.
    """

    #: The permissive value: the catalogue is available, and so is composing.
    DATABASE = "database", "Our recipe database"
    #: The restriction: composed dishes only, the catalogue tools refuse.
    AI = "ai", "Composed by the assistant only"
