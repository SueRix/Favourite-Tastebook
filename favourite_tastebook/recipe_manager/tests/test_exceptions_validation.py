from typing import Any, cast
from unittest.mock import MagicMock

from django.db.models import QuerySet
from django.test import SimpleTestCase

from recipe_manager.domain.exceptions.selectors import EmptyQueryValueError
from recipe_manager.domain.exceptions.services import (
    EmptyIngredientsError,
    InvalidWeightConfigurationError,
)
from recipe_manager.infrastructure.orm.scoring import RecipeScoringService


class ExceptionsValidationTests(SimpleTestCase):
    """
    Input guards live in RecipeScoringService now; they must fire before any ORM work,
    so this stays a SimpleTestCase (no database).
    """

    def _annotate(self, selected_ids, weights=None):
        qs_mock = MagicMock(spec=QuerySet)
        qs_mock.annotate.return_value = qs_mock

        return RecipeScoringService.annotate_recipe_scores(
            qs=cast(QuerySet[Any], qs_mock),
            selected_ids=selected_ids,
            weights=weights,
        )

    def test_raises_empty_query_value_when_none(self):
        with self.assertRaises(EmptyQueryValueError):
            self._annotate(selected_ids=None)

    def test_raises_empty_query_value_when_not_list_like(self):
        with self.assertRaises(EmptyQueryValueError):
            self._annotate(selected_ids=123)

    def test_raises_empty_query_value_when_contains_empty(self):
        with self.assertRaises(EmptyQueryValueError):
            self._annotate(selected_ids=["", "5"])

    def test_raises_empty_ingredients_when_empty_list(self):
        with self.assertRaises(EmptyIngredientsError):
            self._annotate(selected_ids=[])

    def test_raises_invalid_weight_configuration(self):
        with self.assertRaises(InvalidWeightConfigurationError):
            self._annotate(selected_ids=[1], weights={"bad_key": 1})

    def test_validate_selected_ids_accepts_list_tuple_and_set(self):
        for value in ([1, 2], (1, 2), {1, 2}):
            with self.subTest(value=value):
                RecipeScoringService.validate_selected_ids(value)  # must not raise

    def test_known_weight_keys_are_accepted(self):
        # Guards the override contract used by annotate_recipe_scores callers.
        merged = RecipeScoringService._resolve_weights({"required_match": 42})
        self.assertEqual(merged["required_match"], 42)
        self.assertEqual(
            set(merged),
            set(RecipeScoringService.DEFAULT_WEIGHTS),
        )