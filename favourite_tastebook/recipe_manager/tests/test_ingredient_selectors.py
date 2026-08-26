from django.test import TestCase

from recipe_manager.models import Ingredient
from recipe_manager.infrastructure.selectors import IngredientSelector


class IngredientSelectorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.salt = Ingredient.objects.create(name="__ut_salt__", category="__ut_spices__")
        cls.sugar = Ingredient.objects.create(name="__ut_sugar__", category="__ut_spices__")
        cls.milk = Ingredient.objects.create(name="__ut_milk__", category="__ut_dairy__")
        cls.butter = Ingredient.objects.create(name="__ut_butter__", category="__ut_dairy__")

    def test_list_categories_contains_test_categories(self):
        cats = list(IngredientSelector.list_categories())
        self.assertIn("__ut_dairy__", cats)
        self.assertIn("__ut_spices__", cats)

    def test_list_ingredients_filter_by_q_icontains_includes_milk(self):
        qs = IngredientSelector.list_ingredients({"q": "__ut_mi"})
        names = list(qs.values_list("name", flat=True))
        self.assertIn("__ut_milk__", names)

    def test_list_ingredients_filter_by_category_includes_salt_and_sugar(self):
        qs = IngredientSelector.list_ingredients({"category": "__ut_spices__"})
        names = list(qs.values_list("name", flat=True))
        self.assertIn("__ut_salt__", names)
        self.assertIn("__ut_sugar__", names)

    def test_list_ingredients_filter_by_q_and_category_includes_sugar(self):
        qs = IngredientSelector.list_ingredients({"q": "__ut_su", "category": "__ut_spices__"})
        names = list(qs.values_list("name", flat=True))
        self.assertIn("__ut_sugar__", names)

    def test_list_ingredients_ignores_empty_filter_values(self):
        # Blank form fields must not narrow the queryset (falsy values are skipped).
        qs = IngredientSelector.list_ingredients({"q": "", "category": ""})
        names = set(qs.values_list("name", flat=True))
        self.assertTrue({"__ut_salt__", "__ut_milk__"} <= names)

    def test_list_selected_merges_ids_and_ai_names(self):
        # The search form feeds a queryset ("ingredient") and AI-suggested names side by side.
        qs = IngredientSelector.list_selected({
            "ingredient": Ingredient.objects.filter(id=self.salt.id),
            "ai_selected": ["__ut_milk__"],
        })
        self.assertEqual(
            set(qs.values_list("name", flat=True)),
            {"__ut_salt__", "__ut_milk__"},
        )

    def test_list_selected_without_input_returns_empty(self):
        self.assertEqual(list(IngredientSelector.list_selected({})), [])

    def test_is_ai_mode_detects_flag_and_payload(self):
        self.assertTrue(IngredientSelector.is_ai_mode({"ai_mode_active": "1"}))
        self.assertTrue(IngredientSelector.is_ai_mode({"ai_selected": ["__ut_milk__"]}))
        self.assertFalse(IngredientSelector.is_ai_mode({"q": "__ut_mi"}))

    def test_search_by_name_without_query_returns_whole_category(self):
        names = set(
            IngredientSelector.search_by_name("", category="__ut_dairy__")
            .values_list("name", flat=True)
        )
        self.assertEqual(names, {"__ut_milk__", "__ut_butter__"})