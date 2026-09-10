from django.db.models import QuerySet

from recipe_manager.domain.recipe_selection_strategy import RecipeSelectionStrategy
from recipe_manager.infrastructure.selectors import RecipeSelector

MIN_KEYWORD_LENGTH = 2


class KeywordSelectionStrategy(RecipeSelectionStrategy):
    """
    What: Classic, static selection — case-insensitive SQL match on title/description.
    Where: Registered as the "keyword" (default) strategy in SelectRecipesUseCase.
    Why: Wraps the pre-existing RecipeSelector.search_by_keyword behind the strategy
         contract so the old behaviour is preserved 1:1 and stays swappable.
    """

    def select(self, keyword: str, user=None) -> QuerySet:
        from recipe_manager.models import Recipe

        cleaned = (keyword or "").strip()
        if len(cleaned) < MIN_KEYWORD_LENGTH:
            return Recipe.objects.none()

        return RecipeSelector.search_by_keyword(cleaned)
