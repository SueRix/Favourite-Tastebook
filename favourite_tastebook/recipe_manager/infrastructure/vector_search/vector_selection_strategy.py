from django.conf import settings
from django.db.models import Case, IntegerField, QuerySet, Value, When

from recipe_manager.domain.recipe_selection_strategy import RecipeSelectionStrategy
from recipe_manager.infrastructure.vector_search.n8n_client import N8nPineconeClient

MIN_KEYWORD_LENGTH = 2


class VectorSelectionStrategy(RecipeSelectionStrategy):
    """
    What: Semantic selection — delegates the "recall" step to Pinecone (via n8n),
          then hydrates the resulting ids straight from Postgres.
    Where: Registered as the "vector" strategy in SelectRecipesUseCase.
    Why: Fully independent from the SQL keyword path — no RecipeScoringService, no
         ILIKE. Postgres is used ONLY to materialise rows for rendering; the match
         set and its order come entirely from the vector backend.
    """

    def __init__(self, client: N8nPineconeClient = None, top_k: int = None):
        # Constructor injection keeps the strategy unit-testable with a fake client.
        self.client = client or N8nPineconeClient()
        self.top_k = top_k or settings.VECTOR_SEARCH_TOP_K

    def select(self, keyword: str, user=None) -> QuerySet:
        from recipe_manager.models import Recipe

        cleaned = (keyword or "").strip()
        if len(cleaned) < MIN_KEYWORD_LENGTH:
            return Recipe.objects.none()

        matches = self.client.query(cleaned, top_k=self.top_k)
        if not matches:
            return Recipe.objects.none()

        ordered_ids = [recipe_id for recipe_id, _score in matches]

        # Preserve Pinecone's ranking: Postgres would otherwise return arbitrary order.
        # Build a CASE ... WHEN ladder mapping each id to its rank position.
        preserved_order = Case(
            *[When(id=pk, then=Value(pos)) for pos, pk in enumerate(ordered_ids)],
            output_field=IntegerField(),
        )

        return (
            Recipe.objects
            .select_related("cuisine")
            .filter(id__in=ordered_ids)
            .annotate(_vector_rank=preserved_order)
            .order_by("_vector_rank")
        )