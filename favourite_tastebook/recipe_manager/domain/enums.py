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
