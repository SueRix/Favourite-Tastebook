from recipe_manager.models import Recipe, SavedRecipe
from recipe_manager.infrastructure.selectors import RecipeSelector
from recipe_manager.infrastructure.presentation.featured_recipe import FeaturedRecipePresenter

MIN_KEYWORD_LENGTH = 2


class SearchRecipesUseCase:
    """
    Application layer: validates a search keyword and delegates DB access to RecipeSelector.
    """

    @classmethod
    def execute(cls, keyword: str):
        """
        What: Cleans the raw keyword, enforces a minimum length of 2 chars, and returns matching recipes.
        Where: Called by RecipesDatabaseSearchPartialView when an HTMX GET request arrives.
        Why: Keeps validation/cleaning out of the view and ORM out of the application layer.
        """
        cleaned = (keyword or "").strip()

        if len(cleaned) < MIN_KEYWORD_LENGTH:
            return Recipe.objects.none()

        return RecipeSelector.search_by_keyword(cleaned)

    @classmethod
    def get_card_detail(cls, recipe_id, user):
        """
        What: Builds the full presentation context for one recipe's detail modal (title, image, ingredient groups, steps, saved flag).
        Where: Called by RecipesDatabaseCardPartialView when a card is clicked on the Recipes Database page.
        Why: Reuses FeaturedRecipePresenter so the database modal matches the home-page recipe card 1:1, without duplicating presentation logic.
        """
        recipe = RecipeSelector.get_with_ingredients(recipe_id)
        if not recipe:
            return None

        saved_ids = set()
        if user and user.is_authenticated:
            saved_ids = set(
                SavedRecipe.objects
                .filter(user=user)
                .values_list('recipe_id', flat=True)
            )

        featured, _, _ = FeaturedRecipePresenter.select(
            [recipe],
            recipe_id=recipe.id,
            selected_ids=[],
            saved_ids=saved_ids,
        )
        return featured
