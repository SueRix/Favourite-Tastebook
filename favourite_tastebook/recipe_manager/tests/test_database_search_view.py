from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from recipe_manager.application.use_cases.search_recipes import SELECTION_STRATEGIES
from recipe_manager.domain.exceptions import VectorBackendUnavailableError
from recipe_manager.models import Cuisine, Recipe

SEARCH_URL_NAME = "partials_recipes_database_search"
CARD_URL = "/home/partials/database/card/{}/"


class FakeN8nClient:
    """Stand-in for N8nPineconeClient: records calls, returns preset (id, score) tuples. No network."""

    def __init__(self, matches=None, error=None):
        self._matches = matches or []
        self._error = error
        self.calls = []

    def query(self, keyword, top_k):
        self.calls.append((keyword, top_k))
        if self._error:
            raise self._error
        return self._matches


class RecipesDatabaseSearchPartialViewTests(TestCase):
    """
    Covers the wiring the UI depends on: the `mode` query param must reach the
    right engine, and a vector backend outage must not reach the user as a 500.
    """

    @classmethod
    def setUpTestData(cls):
        cls.cuisine = Cuisine.objects.create(name="__ut_view_cuisine__")
        cls.r1 = Recipe.objects.create(title="__ut_view_r1__", cook_time=10, cuisine=cls.cuisine)
        cls.r2 = Recipe.objects.create(title="__ut_view_r2__", cook_time=20, cuisine=cls.cuisine)
        cls.r3 = Recipe.objects.create(title="__ut_view_r3__", cook_time=30, cuisine=cls.cuisine)

    def _get(self, **params):
        return self.client.get(reverse(SEARCH_URL_NAME), params)

    def _vector_client(self, **kwargs):
        """Swaps the client on the module-level vector strategy for the duration of a test."""
        fake = FakeN8nClient(**kwargs)
        patcher = patch.object(SELECTION_STRATEGIES["vector"], "client", fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def test_vector_mode_preserves_backend_ranking_in_rendered_html(self):
        # Backend ranks r3 > r1 > r2; the cards must be rendered in that order.
        self._vector_client(matches=[(self.r3.id, 0.9), (self.r1.id, 0.8), (self.r2.id, 0.7)])

        response = self._get(keyword="creamy tomato soup", mode="vector")
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        positions = [html.index(CARD_URL.format(pk)) for pk in (self.r3.id, self.r1.id, self.r2.id)]
        self.assertEqual(positions, sorted(positions))

    def test_vector_mode_reaches_the_vector_engine(self):
        fake = self._vector_client(matches=[(self.r1.id, 0.9)])

        self._get(keyword="  borscht  ", mode="vector")

        self.assertEqual(fake.calls, [("borscht", SELECTION_STRATEGIES["vector"].top_k)])

    def test_unknown_mode_silently_falls_back_to_keyword(self):
        # Documents the fallback in SearchRecipesUseCase.execute: a typo in `mode`
        # must not blow up, and must never spend an embedding call.
        fake = self._vector_client(matches=[(self.r1.id, 0.9)])

        response = self._get(keyword="__ut_view_r1__", mode="not-a-mode")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(fake.calls, [])

    def test_missing_mode_defaults_to_keyword(self):
        fake = self._vector_client(matches=[(self.r1.id, 0.9)])

        response = self._get(keyword="__ut_view_r1__")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(fake.calls, [])

    def test_short_keyword_in_vector_mode_never_hits_the_backend(self):
        fake = self._vector_client(matches=[(self.r1.id, 0.9)])

        response = self._get(keyword="a", mode="vector")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rdb-hint")
        self.assertEqual(fake.calls, [])

    def test_backend_outage_renders_error_partial_instead_of_500(self):
        # HTMX swaps the response straight into #rdb-results, so a 500 would put
        # Django's error page inside the results area.
        self._vector_client(error=VectorBackendUnavailableError("n8n webhook request failed"))

        response = self._get(keyword="creamy tomato soup", mode="vector")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rdb-error")
        self.assertContains(response, VectorBackendUnavailableError.message)
        # Transport details (webhook URL, HTTP body) belong in the logs, not the page.
        self.assertNotContains(response, "n8n")

    def test_keyword_mode_is_unaffected_by_a_dead_vector_backend(self):
        self._vector_client(error=VectorBackendUnavailableError("n8n webhook request failed"))

        response = self._get(keyword="__ut_view_r1__", mode="keyword")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "rdb-error")
