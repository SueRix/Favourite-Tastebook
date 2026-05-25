from django.db.models import Prefetch, Q

from recipe_manager.models import Recipe, RecipeIngredient, SavedRecipe

class RecipeSelector:
    @classmethod
    def get_base_queryset(cls):
        return Recipe.objects.select_related("cuisine").all()

    @classmethod
    def search_by_keyword(cls, keyword: str):
        """
        What: Returns recipes whose title OR description contains the given keyword (case-insensitive).
        Where: Used by SearchRecipesUseCase to feed the Recipes Database HTMX search partial.
        Why: Centralises ORM access for keyword search so the use case stays free of Django query syntax.
        """
        return (
            Recipe.objects
            .select_related("cuisine")
            .filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
            .order_by("title")
        )

    @classmethod
    def get_with_ingredients(cls, recipe_id):
        """
        What: Returns a single Recipe with its cuisine and ingredients prefetched, or None.
        Where: Used by SearchRecipesUseCase.get_card_detail to populate the recipe detail modal.
        Why: Centralises the prefetch logic required to render the full detailed card view.
        """
        return (
            Recipe.objects
            .select_related("cuisine")
            .prefetch_related(
                Prefetch(
                    "ingredients",
                    queryset=(
                        RecipeIngredient.objects
                        .select_related("ingredient")
                        .order_by("importance", "ingredient__name")
                    ),
                )
            )
            .filter(id=recipe_id)
            .first()
        )


class RecipeSaver:
    @classmethod
    def get_user_saved_recipes(cls, user):
        return SavedRecipe.objects.filter(user=user).select_related(
            'recipe',
            'recipe__cuisine'
        )