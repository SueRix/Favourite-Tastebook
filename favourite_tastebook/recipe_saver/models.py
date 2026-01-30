from django.db import models
from django.conf import settings
from recipe_manager.models import Recipe

class SavedRecipe(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_recipes'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='saved_by_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')
        ordering = ['-created_at']
        verbose_name = "Saved Recipe"

    def __str__(self):
        return f"{self.user.username} -> {self.recipe.title}"