from django.test import TestCase

from recipe_manager.models import Cuisine, Recipe
from recipe_manager.infrastructure.vector_search.vector_selection_strategy import (
    INGREDIENT_QUERY_TEMPLATE,
    VectorSelectionStrategy,
)


class FakeN8nClient:
    """Stand-in for N8nPineconeClient: records calls, returns preset (id, score) tuples. No network."""

    def __init__(self, matches):
        self._matches = matches
        self.calls = []

    def query(self, keyword, top_k):
        self.calls.append((keyword, top_k))
        return self._matches


class VectorSelectionStrategyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cuisine = Cuisine.objects.create(name="__ut_vec_cuisine__")
        cls.r1 = Recipe.objects.create(title="__ut_vec_r1__", cook_time=10, cuisine=cls.cuisine)
        cls.r2 = Recipe.objects.create(title="__ut_vec_r2__", cook_time=20, cuisine=cls.cuisine)
        cls.r3 = Recipe.objects.create(title="__ut_vec_r3__", cook_time=30, cuisine=cls.cuisine)

    def _strategy(self, matches, top_k=20):
        return VectorSelectionStrategy(client=FakeN8nClient(matches), top_k=top_k)

    def test_preserves_pinecone_ranking_order(self):
        # Backend ranks r3 > r1 > r2; Postgres must not reorder them.
        matches = [(self.r3.id, 0.9), (self.r1.id, 0.8), (self.r2.id, 0.7)]
        qs = self._strategy(matches).select("borscht")
        self.assertEqual(
            list(qs.values_list("id", flat=True)),
            [self.r3.id, self.r1.id, self.r2.id],
        )

    def test_one_char_keyword_short_circuits_without_hitting_backend(self):
        fake = FakeN8nClient([(self.r1.id, 1.0)])
        qs = VectorSelectionStrategy(client=fake, top_k=20).select("a")
        self.assertEqual(list(qs), [])
        self.assertEqual(fake.calls, [])  # min-length rule runs before any network call

    def test_whitespace_only_keyword_short_circuits(self):
        # "   " strips to "" -> shorter than min length -> no backend call.
        fake = FakeN8nClient([(self.r1.id, 1.0)])
        qs = VectorSelectionStrategy(client=fake, top_k=20).select("   ")
        self.assertEqual(list(qs), [])
        self.assertEqual(fake.calls, [])

    def test_two_char_keyword_is_accepted_and_calls_backend(self):
        # Boundary: exactly MIN_KEYWORD_LENGTH must pass through.
        fake = FakeN8nClient([(self.r1.id, 0.5)])
        qs = VectorSelectionStrategy(client=fake, top_k=20).select("ab")
        self.assertEqual(list(qs.values_list("id", flat=True)), [self.r1.id])
        self.assertEqual(fake.calls, [("ab", 20)])

    def test_empty_matches_returns_empty_queryset(self):
        qs = self._strategy([]).select("nothing here")
        self.assertEqual(list(qs), [])

    def test_stale_ids_from_pinecone_are_ignored(self):
        # Pinecone still has a vector for a recipe that was deleted in Postgres.
        matches = [(self.r1.id, 0.9), (999_999, 0.8)]
        qs = self._strategy(matches).select("borscht")
        self.assertEqual(list(qs.values_list("id", flat=True)), [self.r1.id])

    def test_keyword_is_trimmed_and_top_k_forwarded(self):
        fake = FakeN8nClient([(self.r1.id, 1.0)])
        VectorSelectionStrategy(client=fake, top_k=5).select("  borscht  ")
        self.assertEqual(fake.calls, [("borscht", 5)])

    def test_scores_are_annotated_onto_the_queryset(self):
        # The presentation layer draws the thermometer from this annotation;
        # dropping it here would mean a second round-trip just to render a bar.
        qs = self._strategy([(self.r2.id, 0.81), (self.r1.id, 0.42)]).select("borscht")
        self.assertEqual(
            [round(r.vector_score, 2) for r in qs],
            [0.81, 0.42],
        )

    def test_ingredient_template_reframes_the_query_sent_to_the_backend(self):
        fake = FakeN8nClient([(self.r1.id, 0.7)])
        strategy = VectorSelectionStrategy(
            client=fake, top_k=20, query_template=INGREDIENT_QUERY_TEMPLATE,
        )

        strategy.select("  smoked paprika  ")

        self.assertEqual(fake.calls, [("recipes made with smoked paprika", 20)])

    def test_default_template_sends_the_keyword_verbatim(self):
        fake = FakeN8nClient([(self.r1.id, 0.7)])

        VectorSelectionStrategy(client=fake, top_k=20).select("borscht")

        self.assertEqual(fake.calls, [("borscht", 20)])
