# js/tests/test_recipe_selectors.py
from django.test import TestCase

from recipe_manager.domain.enums import Importance
from recipe_manager.models import Cuisine, Ingredient, Recipe, RecipeIngredient
from recipe_manager.infrastructure.selectors.recipes import search_recipes_by_ingredients


class RecipeSelectorsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cuisine = Cuisine.objects.create(name="__ut_cuisine_selectors__")

        cls.i_a = Ingredient.objects.create(name="__ut_sel_ing_a__", category="__ut_sel_cat__")
        cls.i_b = Ingredient.objects.create(name="__ut_sel_ing_b__", category="__ut_sel_cat__")
        cls.i_c = Ingredient.objects.create(name="__ut_sel_ing_c__", category="__ut_sel_cat__")

        cls.r_full = Recipe.objects.create(title="__ut_sel_full__", cook_time=30, cuisine=cuisine)
        cls.r_partial = Recipe.objects.create(title="__ut_sel_partial__", cook_time=5, cuisine=cuisine)
        cls.r_none = Recipe.objects.create(title="__ut_sel_none__", cook_time=1, cuisine=cuisine)

        RecipeIngredient.objects.create(recipe=cls.r_full, ingredient=cls.i_a, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r_full, ingredient=cls.i_b, amount=1, importance=Importance.REQUIRED)

        RecipeIngredient.objects.create(recipe=cls.r_partial, ingredient=cls.i_a, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r_partial, ingredient=cls.i_b, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r_partial, ingredient=cls.i_c, amount=1, importance=Importance.OPTIONAL)

        RecipeIngredient.objects.create(recipe=cls.r_none, ingredient=cls.i_c, amount=1, importance=Importance.REQUIRED)

    def test_non_strict_returns_any_with_matches(self):
        qs = search_recipes_by_ingredients(selected_ids=[self.i_a.id], strict_required=False)
        qs = qs.filter(id__in=[self.r_full.id, self.r_partial.id, self.r_none.id])

        titles = set(qs.values_list("title", flat=True))
        self.assertIn(self.r_full.title, titles)
        self.assertIn(self.r_partial.title, titles)
        self.assertNotIn(self.r_none.title, titles)

    def test_strict_requires_all_required(self):
        qs = search_recipes_by_ingredients(selected_ids=[self.i_a.id], strict_required=True)
        qs = qs.filter(id__in=[self.r_full.id, self.r_partial.id, self.r_none.id])
        self.assertEqual(list(qs.values_list("id", flat=True)), [])

        qs = search_recipes_by_ingredients(selected_ids=[self.i_a.id, self.i_b.id], strict_required=True)
        qs = qs.filter(id__in=[self.r_full.id, self.r_partial.id, self.r_none.id])

        titles = set(qs.values_list("title", flat=True))
        self.assertIn(self.r_full.title, titles)
        self.assertIn(self.r_partial.title, titles)
        self.assertNotIn(self.r_none.title, titles)

    def test_ordering_returns_only_expected_subset(self):
        qs = search_recipes_by_ingredients(selected_ids=[self.i_a.id, self.i_b.id], strict_required=False)
        qs = qs.filter(id__in=[self.r_full.id, self.r_partial.id, self.r_none.id])

        titles = set(qs.values_list("title", flat=True))
        self.assertEqual(titles, {self.r_full.title, self.r_partial.title})
