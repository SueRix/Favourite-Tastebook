from typing import Any, cast
from unittest.mock import MagicMock

from django.db.models import QuerySet
from django.test import SimpleTestCase

from recipe_manager.domain.exceptions.selectors import EmptyQueryValueError
from recipe_manager.domain.exceptions.services import (
    EmptyIngredientsError,
    InvalidWeightConfigurationError,
)
from recipe_manager.selectors.selection_recipes import search_recipes_by_ingredients
from recipe_manager.services.recipe_selection_service import annotate_recipe_scores


class ExceptionsValidationTests(SimpleTestCase):
    def test_search_raises_empty_query_value_when_none(self):
        with self.assertRaises(EmptyQueryValueError):
            search_recipes_by_ingredients(selected_ids=None, strict_required=False)

    def test_search_raises_empty_query_value_when_not_list_like(self):
        with self.assertRaises(EmptyQueryValueError):
            search_recipes_by_ingredients(selected_ids=123, strict_required=False)

    def test_search_raises_empty_query_value_when_contains_empty(self):
        with self.assertRaises(EmptyQueryValueError):
            search_recipes_by_ingredients(selected_ids=["", "5"], strict_required=False)

    def test_search_raises_empty_ingredients_when_empty_list(self):
        with self.assertRaises(EmptyIngredientsError):
            search_recipes_by_ingredients(selected_ids=[], strict_required=False)

    def test_annotate_raises_invalid_weight_configuration(self):
        qs_mock = MagicMock(spec=QuerySet)
        qs_mock.annotate.return_value = qs_mock

        with self.assertRaises(InvalidWeightConfigurationError):
            annotate_recipe_scores(
                qs=cast(QuerySet[Any], qs_mock),
                selected_ids=[1],
                weights={"bad_key": 1},
            )
