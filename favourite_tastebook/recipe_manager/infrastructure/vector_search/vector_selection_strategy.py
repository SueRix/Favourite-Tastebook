from django.conf import settings
from django.db.models import Case, FloatField, IntegerField, QuerySet, Value, When

from recipe_manager.domain.recipe_selection_strategy import RecipeSelectionStrategy
from recipe_manager.infrastructure.vector_search.n8n_client import N8nPineconeClient

MIN_KEYWORD_LENGTH = 2

# Sent to the backend as-is: the user's own words are the query.
PLAIN_QUERY_TEMPLATE = "{keyword}"

# Nudges the same recipe index towards ingredient-centric documents. There is no
# separate ingredient index, so the framing of the sentence is what steers the
# embedding; keep it a full phrase rather than a bare noun.
INGREDIENT_QUERY_TEMPLATE = "recipes made with {keyword}"


class VectorSelectionStrategy(RecipeSelectionStrategy):
    """
    What: Semantic selection — delegates the "recall" step to Pinecone (via n8n),
          then hydrates the resulting ids straight from Postgres.
    Where: Registered as the "vector" and "ingredient" strategies in SelectRecipesUseCase.
    Why: Fully independent from the SQL keyword path — no RecipeScoringService, no
         ILIKE. Postgres is used ONLY to materialise rows for rendering; the match
         set, its order and its scores come entirely from the vector backend.
    """

    def __init__(self, client: N8nPineconeClient = None, top_k: int = None,
                 query_template: str = PLAIN_QUERY_TEMPLATE):
        # Constructor injection keeps the strategy unit-testable with a fake client.
        self.client = client or N8nPineconeClient()
        self.top_k = top_k or settings.VECTOR_SEARCH_TOP_K
        # Only the wording sent to the backend differs between semantic modes,
        # so one class covers them all instead of a subclass per phrasing.
        self.query_template = query_template

    def select(self, keyword: str, user=None) -> QuerySet:
        from recipe_manager.models import Recipe

        cleaned = (keyword or "").strip()
        if len(cleaned) < MIN_KEYWORD_LENGTH:
            return Recipe.objects.none()

        matches = self.client.query(self.query_template.format(keyword=cleaned), top_k=self.top_k)
        if not matches:
            return Recipe.objects.none()

        ordered_ids = [recipe_id for recipe_id, _score in matches]

        # Preserve Pinecone's ranking: Postgres would otherwise return arbitrary order.
        # Build a CASE ... WHEN ladder mapping each id to its rank position.
        preserved_order = Case(
            *[When(id=pk, then=Value(pos)) for pos, pk in enumerate(ordered_ids)],
            output_field=IntegerField(),
        )

        # Carry the similarity itself into the queryset as well: the presentation
        # layer turns it into the match thermometer, and losing it here would mean
        # a second round-trip to the backend just to draw a bar.
        preserved_score = Case(
            *[When(id=pk, then=Value(score)) for pk, score in matches],
            output_field=FloatField(),
        )

        return (
            Recipe.objects
            .select_related("cuisine")
            .filter(id__in=ordered_ids)
            .annotate(_vector_rank=preserved_order, vector_score=preserved_score)
            .order_by("_vector_rank")
        )
