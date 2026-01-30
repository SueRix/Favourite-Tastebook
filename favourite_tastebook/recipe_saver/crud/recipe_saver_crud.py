from django.db import IntegrityError
from recipe_manager.models import Recipe
from ..models import SavedRecipe
from ..exceptions import RecipeAlreadySavedError, RecipeNotFoundError

def add_recipe_to_saved(user, recipe_id):
    try:
        recipe = Recipe.objects.get(id=recipe_id)
    except Recipe.objects.model.DoesNotExist:
        raise RecipeNotFoundError()

    try:
        return SavedRecipe.objects.create(user=user, recipe=recipe)
    except IntegrityError:
        raise RecipeAlreadySavedError()

def remove_recipe_from_saved(user, recipe_id):
    deleted_count, _ = SavedRecipe.objects.filter(user=user, recipe_id=recipe_id).delete()
    if deleted_count == 0:
        raise RecipeNotFoundError()

def get_user_saved_recipes(user):
    return SavedRecipe.objects.filter(user=user).select_related('recipe', 'recipe__cuisine')