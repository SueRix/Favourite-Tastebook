from recipe_manager.models import Recipe, SavedRecipe
from recipe_manager.infrastructure.selectors import RecipeSelector
from recipe_manager.infrastructure.presentation.featured_recipe import FeaturedRecipePresenter
from recipe_manager.infrastructure.orm.keyword_selection_strategy import KeywordSelectionStrategy
from recipe_manager.infrastructure.vector_search.vector_selection_strategy import (
    INGREDIENT_QUERY_TEMPLATE,
    VectorSelectionStrategy,
)

# Client-facing mode -> concrete selection strategy.
# The branches are fully independent engines; neither knows about the other.
# "vector" and "ingredient" share one engine and differ only in how the query
# is phrased for the embedding, since there is a single recipe index behind it.
SELECTION_STRATEGIES = {
    "keyword": KeywordSelectionStrategy(),
    "vector": VectorSelectionStrategy(),
    "ingredient": VectorSelectionStrategy(query_template=INGREDIENT_QUERY_TEMPLATE),
}
DEFAULT_SELECTION_MODE = "keyword"


class SearchRecipesUseCase:
    """
    Application layer: validates a search keyword and dispatches it to the
    selection strategy chosen by the client (static SQL vs. vector similarity).
    """

    @classmethod
    def execute(cls, keyword: str, mode: str = DEFAULT_SELECTION_MODE, user=None):
        """
        What: Picks the selection strategy requested by the client and runs it.
        Where: Called by RecipesDatabaseSearchPartialView when an HTMX GET request arrives.
        Why: Keeps validation/cleaning and engine choice out of the view; each strategy
             owns its own cleaning + min-length rule, so the two paths stay independent.
        """
        strategy = SELECTION_STRATEGIES.get(mode) or SELECTION_STRATEGIES[DEFAULT_SELECTION_MODE]
        return strategy.select(keyword, user=user)

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
