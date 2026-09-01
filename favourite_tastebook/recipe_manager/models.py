from django.conf import settings
from django.db import models

from .domain.enums import AgentRecipeSource, Units, Importance, TasteLevels


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
    image_url = models.ImageField(upload_to="recipe_photos/", blank=True, null=True)
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
    recipe = models.ForeignKey(
        "Recipe",
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    ingredient = models.ForeignKey(
        "Ingredient",
        on_delete=models.PROTECT,
        related_name="used_in_recipes",
    )

    amount = models.DecimalField(max_digits=6, decimal_places=2)
    unit = models.CharField(
        max_length=10,
        choices=Units,
        default=Units.GRAM,
    )

    importance = models.CharField(
        max_length=12,
        choices=Importance,
        default=Importance.REQUIRED,
    )

    class Meta:
        unique_together = ("recipe", "ingredient")
        verbose_name = "Ingredient using in recipe"

class SavedRecipe(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_recipes'
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='saved_by_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'recipe')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} saved {self.recipe}"

class UserTastePreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='taste_preferences'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='favored_by_users'
    )
    score = models.SmallIntegerField(
        choices=TasteLevels,
        default=TasteLevels.NEUTRAL
    )
    is_explicit = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "ingredient")
        verbose_name = "User Taste Preference"

    def __str__(self):
        return f"{self.user.username} - {self.ingredient.name}: {self.score}"

class UserCuisinePreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cuisine_preferences'
    )
    cuisine = models.ForeignKey(
        Cuisine,
        on_delete=models.CASCADE,
        related_name='favored_by_users'
    )
    score = models.SmallIntegerField(
        choices=TasteLevels,
        default=TasteLevels.NEUTRAL
    )

    class Meta:
        unique_together = ("user", "cuisine")
        verbose_name = "User Cuisine Preference"

    def __str__(self):
        return f"{self.user.username} - {self.cuisine.name}: {self.score}"

class GeneratedRecipe(models.Model):
    """
    What: A dish the cooking agent composed out of the model's own knowledge and
          the user decided to keep.
    Where: Written by SaveGeneratedRecipeUseCase, called from the agent tool API.
    Why: These recipes are not part of the curated catalogue — nobody reviewed
         them, they have no photo and they are absent from the vector index. Put
         in the Recipe table they would quietly mix invented dishes into the
         database page, the home feed and every search. So they live in their own
         table, owned by the user who asked for them, while their ingredients
         still point at the shared Ingredient catalogue: that is what keeps taste
         preferences and the never_use rule enforceable on them.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_recipes",
    )
    title = models.CharField(max_length=255)
    # Free text on purpose: a generated dish must not extend the curated Cuisine
    # list, which drives the cuisine preference panel.
    cuisine = models.CharField(max_length=100, blank=True)
    cook_time = models.PositiveIntegerField(help_text="Time in minutes")
    steps = models.JSONField(default=list)
    # Which conversation produced it — useful when a user asks "what did you
    # suggest me yesterday", and for tracing a bad recipe back to its dialogue.
    session_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Per user, not global: two people may well keep their own "Chicken Soup".
        unique_together = ("user", "title")
        ordering = ["-created_at"]
        verbose_name = "Generated Recipe"

    def __str__(self):
        return f"{self.title} (generated for {self.user})"


class GeneratedRecipeIngredient(models.Model):
    """
    Mirrors RecipeIngredient, but for generated recipes. The FK to Ingredient is
    deliberate: the agent may only compose a dish out of the existing catalogue,
    so every line here is a known ingredient and can be checked against the
    user's taboo list before the recipe is stored.
    """

    generated_recipe = models.ForeignKey(
        GeneratedRecipe,
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name="used_in_generated_recipes",
    )

    amount = models.DecimalField(max_digits=6, decimal_places=2)
    unit = models.CharField(max_length=10, choices=Units, default=Units.GRAM)
    importance = models.CharField(
        max_length=12,
        choices=Importance,
        default=Importance.REQUIRED,
    )

    class Meta:
        unique_together = ("generated_recipe", "ingredient")
        verbose_name = "Ingredient using in generated recipe"


class AgentPreference(models.Model):
    """
    What: How one user wants the cooking assistant to behave — the three answers
          the studio's settings panel collects.
    Where: Read by the agent chat use case before every turn and by every tool
           endpoint that one of the answers restricts; written by the settings
           endpoint behind the gear button in the studio.
    Why: These are instructions to a language model, and a model can be talked
         out of an instruction. Storing them as rows lets the enforcement live in
         our code — the tools simply refuse what the user switched off — while
         the same values also travel to the prompt so the assistant can explain
         itself instead of hitting a wall it was never told about.

    A missing row is a valid state and means the defaults below. Nothing is
    written until somebody actually moves a switch, so opening the studio stays
    a read.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_preference",
    )

    #: Whether the assistant may tailor a dish to the taste profile. Off does NOT
    #: lift the never_use list: that one is a hard exclusion (it carries the
    #: allergies), and it stays enforced in SaveGeneratedRecipeUseCase either way.
    use_tastes = models.BooleanField(default=True)

    #: DATABASE is the default because it is the permissive value: the
    #: assistant may look a dish up in the catalogue AND compose one, which is
    #: what it could always do. AI is the restriction — it takes the catalogue
    #: away, and the two search tools refuse outright while it is set.
    recipe_source = models.CharField(
        max_length=16,
        choices=AgentRecipeSource,
        default=AgentRecipeSource.DATABASE,
    )

    #: Whether a proposed dish may drop straight into the draft editor. Off keeps
    #: the proposal a card in the chat that the person moves across by hand.
    autosave_drafts = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Assistant Preference"

    def __str__(self):
        return f"Assistant preferences of {self.user}"
