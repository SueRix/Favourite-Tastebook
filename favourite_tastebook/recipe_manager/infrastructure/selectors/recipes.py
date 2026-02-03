from recipe_manager.models import Recipe, SavedRecipe

class RecipeSelector:
    @classmethod
    def get_base_queryset(cls):
        return Recipe.objects.select_related("cuisine").all()


class RecipeSaver:
    @classmethod
    def get_user_saved_recipes(cls, user):
        return SavedRecipe.objects.filter(user=user).select_related(
            'recipe',
            'recipe__cuisine'
        )