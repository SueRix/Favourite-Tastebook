from django.test import TestCase

from recipe_manager.models import Ingredient
from recipe_manager.infrastructure.selectors import (
    get_ingredients,
    get_ingredient_categories,
)


class IngredientSelectorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.salt = Ingredient.objects.create(name="__ut_salt__", category="__ut_spices__")
        cls.sugar = Ingredient.objects.create(name="__ut_sugar__", category="__ut_spices__")
        cls.milk = Ingredient.objects.create(name="__ut_milk__", category="__ut_dairy__")
        cls.butter = Ingredient.objects.create(name="__ut_butter__", category="__ut_dairy__")

    def test_get_categories_contains_test_categories(self):
        cats = list(get_ingredient_categories())
        self.assertIn("__ut_dairy__", cats)
        self.assertIn("__ut_spices__", cats)

    def test_get_ingredients_filter_by_q_icontains_includes_milk(self):
        qs = get_ingredients(q="__ut_mi")
        names = list(qs.values_list("name", flat=True))
        self.assertIn("__ut_milk__", names)

    def test_get_ingredients_filter_by_category_includes_salt_and_sugar(self):
        qs = get_ingredients(category="__ut_spices__")
        names = list(qs.values_list("name", flat=True))
        self.assertIn("__ut_salt__", names)
        self.assertIn("__ut_sugar__", names)

    def test_get_ingredients_filter_by_q_and_category_includes_sugar(self):
        qs = get_ingredients(q="__ut_su", category="__ut_spices__")
        names = list(qs.values_list("name", flat=True))
        self.assertIn("__ut_sugar__", names)
