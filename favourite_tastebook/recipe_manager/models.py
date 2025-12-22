from django.db import models


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    category = models.CharField(max_length=100, db_index=True)

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super(Ingredient, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class Cuisine(models.Model):
    name = models.CharField(max_length=100, unique=True)

class Recipe(models.Model):
    title = models.CharField(max_length=512, unique=True)
    description = models.TextField(blank=True)
    cook_time = models.PositiveIntegerField(help_text="Time in minutes")
    image_url = models.URLField(blank=True, null=True)
    cuisine = models.ForeignKey(
        Cuisine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recipes'
    )

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    class Units(models.TextChoices):
        GRAM = "g"
        KILOGRAM = "kg"
        LITER = "l"
        PIECE = "pcs"
        TABLESPOON = "tbsp"
        TEASPOON = "tsp"
        PINCH = "pinch"

    class Importance(models.TextChoices):
        REQUIRED = "required"
        SECONDARY = "secondary"
        OPTIONAL = "optional"

    recipe = models.ForeignKey(Recipe,
                               on_delete=models.CASCADE,
                               related_name='ingredients')

    ingredient = models.ForeignKey(Ingredient,
                                   on_delete=models.PROTECT,
                                   related_name='used_in_recipes')

    amount = models.DecimalField(decimal_places=2, max_digits=6)
    unit = models.CharField(max_length=10,
                            choices=Units,
                            default=Units.GRAM)

    importance = models.CharField(max_length=12,
                                  choices=Importance,
                                  default=Importance.REQUIRED)

    class Meta:
        unique_together = ('recipe', 'ingredient')
        verbose_name = 'Ingredient using in recipe'

    def __str__(self):
        return f"{self.ingredient.name} ({self.amount} {self.unit} for {self.recipe})"
