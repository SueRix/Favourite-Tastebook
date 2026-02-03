from recipe_manager.models import Recipe, SavedRecipe
from recipe_manager.infrastructure.selectors import recipe as selectors
from recipe_manager.infrastructure.presentation.saved_recipe import SavedRecipePresenter
from recipe_manager.domain.exceptions.saved_recipe import (
    RecipeAlreadySavedError,
    RecipeNotFoundError
)
from django.db import IntegrityError


class SavedRecipesUseCase:
    """
    Application layer: orchestrates saved recipes logic.
    Hides Selectors, Presenters and ORM from the View.
    """

    @classmethod
    def build_saved_list(cls, user):
        """
        Orchestrates fetching and presenting the saved recipes list.
        Returns the specific list for the ListView queryset or full context.
        """
        queryset = selectors.get_user_saved_recipes(user)

        presenter = SavedRecipePresenter(queryset)
        formatted_data = presenter.data()

        return {
            "saved_recipes": formatted_data,
            "count": len(formatted_data)
        }

    @classmethod
    def add_to_saved(cls, user, recipe_id):
        """
        Business logic for adding a recipe.
        """
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            raise RecipeNotFoundError()

        try:
            SavedRecipe.objects.create(user=user, recipe=recipe)
        except IntegrityError:
            raise RecipeAlreadySavedError()

    @classmethod
    def remove_from_saved(cls, user, recipe_id):
        """
        Business logic for removing a recipe.
        """
        deleted_count, _ = SavedRecipe.objects.filter(
            user=user,
            recipe_id=recipe_id
        ).delete()

        if deleted_count == 0:
            raise RecipeNotFoundError()