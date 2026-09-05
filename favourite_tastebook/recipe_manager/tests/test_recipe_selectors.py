from django.contrib.auth import get_user_model
from django.test import TestCase

from recipe_manager.domain.enums import Importance, TasteLevels
from recipe_manager.infrastructure.orm.recipe_search import RecipeSearchORM
from recipe_manager.models import (
    Cuisine,
    Ingredient,
    Recipe,
    RecipeIngredient,
    UserCuisinePreference,
    UserTastePreference,
)


class RecipeSearchORMTests(TestCase):
    """
    Covers ingredient-based recipe search as it works today: RecipeSearchORM.find_recipes
    scores every recipe and drops relevance_tier 3 (no useful overlap with the selection).
    """

    @classmethod
    def setUpTestData(cls):
        cls.cuisine = Cuisine.objects.create(name="__ut_cuisine_selectors__")

        cls.i_a = Ingredient.objects.create(name="__ut_sel_ing_a__", category="__ut_sel_cat__")
        cls.i_b = Ingredient.objects.create(name="__ut_sel_ing_b__", category="__ut_sel_cat__")
        cls.i_c = Ingredient.objects.create(name="__ut_sel_ing_c__", category="__ut_sel_cat__")

        cls.r_full = Recipe.objects.create(title="__ut_sel_full__", cook_time=30, cuisine=cls.cuisine)
        cls.r_partial = Recipe.objects.create(title="__ut_sel_partial__", cook_time=5, cuisine=cls.cuisine)
        cls.r_none = Recipe.objects.create(title="__ut_sel_none__", cook_time=1, cuisine=cls.cuisine)

        RecipeIngredient.objects.create(recipe=cls.r_full, ingredient=cls.i_a, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r_full, ingredient=cls.i_b, amount=1, importance=Importance.REQUIRED)

        RecipeIngredient.objects.create(recipe=cls.r_partial, ingredient=cls.i_a, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r_partial, ingredient=cls.i_b, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r_partial, ingredient=cls.i_c, amount=1, importance=Importance.OPTIONAL)

        RecipeIngredient.objects.create(recipe=cls.r_none, ingredient=cls.i_c, amount=1, importance=Importance.REQUIRED)

    def _find(self, ingredient_ids, user=None, **extra_filters):
        """Runs the search, then narrows to this test's fixtures (the DB also holds seeded recipes)."""
        filters = {"ingredient": Ingredient.objects.filter(id__in=ingredient_ids)}
        filters.update(extra_filters)
        return RecipeSearchORM.find_recipes(filters, user=user).filter(
            id__in=[self.r_full.id, self.r_partial.id, self.r_none.id]
        )

    def test_recipes_without_any_match_are_dropped(self):
        titles = set(self._find([self.i_a.id]).values_list("title", flat=True))
        self.assertIn(self.r_full.title, titles)
        self.assertIn(self.r_partial.title, titles)
        self.assertNotIn(self.r_none.title, titles)  # only ingredient is i_c -> tier 3

    def test_empty_selection_returns_nothing(self):
        self.assertEqual(list(RecipeSearchORM.find_recipes({})), [])
        self.assertEqual(list(self._find([])), [])

    def test_ordering_prefers_higher_score(self):
        # Everything matches at least one required ingredient -> same tier, so score decides.
        # r_partial 2 required + 1 optional (21) > r_full 2 required (20) > r_none 1 required (10).
        ids = list(
            self._find([self.i_a.id, self.i_b.id, self.i_c.id]).values_list("id", flat=True)
        )
        self.assertEqual(ids, [self.r_partial.id, self.r_full.id, self.r_none.id])

    def test_required_match_outranks_optional_only_match(self):
        # r_none matches i_c as REQUIRED (tier 1); r_partial only as OPTIONAL (tier 2).
        ids = list(self._find([self.i_c.id]).values_list("id", flat=True))
        self.assertEqual(ids, [self.r_none.id, self.r_partial.id])
        self.assertNotIn(self.r_full.id, ids)

    def test_strict_mode_penalises_missing_required_ingredients(self):
        # Both modes keep the recipe; strict subtracts a penalty per missing required item.
        normal = self._find([self.i_a.id]).get(id=self.r_full.id)
        strict = self._find([self.i_a.id], strict="1").get(id=self.r_full.id)

        self.assertEqual(strict.missing_required, 1)
        self.assertLess(strict.score, normal.score)

    def test_strict_mode_keeps_fully_covered_recipe_at_full_score(self):
        # Nothing is missing, so the penalty term is zero and strict == normal.
        normal = self._find([self.i_a.id, self.i_b.id]).get(id=self.r_full.id)
        strict = self._find([self.i_a.id, self.i_b.id], strict="1").get(id=self.r_full.id)

        self.assertEqual(strict.missing_required, 0)
        self.assertEqual(strict.score, normal.score)

    def test_ai_mode_adds_density_bonus(self):
        # AI mode rewards how many ingredients overlap, on top of the base score.
        normal = self._find([self.i_a.id, self.i_b.id]).get(id=self.r_full.id)
        ai = self._find([self.i_a.id, self.i_b.id], ai_mode_active="1").get(id=self.r_full.id)

        self.assertEqual(ai.total_matches, 2)
        self.assertGreater(ai.score, normal.score)


class RecipeSearchORMTastePreferenceTests(TestCase):
    """The hard taste filters only apply to an authenticated user with use_tastes on."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="__ut_taste_user__", password="__ut_pwd__"
        )
        cls.cuisine_ok = Cuisine.objects.create(name="__ut_taste_ok__")
        cls.cuisine_hated = Cuisine.objects.create(name="__ut_taste_hated__")

        cls.i_a = Ingredient.objects.create(name="__ut_taste_ing_a__", category="__ut_taste_cat__")
        cls.i_hated = Ingredient.objects.create(name="__ut_taste_ing_hated__", category="__ut_taste_cat__")

        cls.r_clean = Recipe.objects.create(title="__ut_taste_clean__", cook_time=10, cuisine=cls.cuisine_ok)
        cls.r_with_hated = Recipe.objects.create(title="__ut_taste_hated_ing__", cook_time=10, cuisine=cls.cuisine_ok)
        cls.r_hated_cuisine = Recipe.objects.create(title="__ut_taste_hated_cui__", cook_time=10, cuisine=cls.cuisine_hated)

        for recipe in (cls.r_clean, cls.r_with_hated, cls.r_hated_cuisine):
            RecipeIngredient.objects.create(
                recipe=recipe, ingredient=cls.i_a, amount=1, importance=Importance.REQUIRED
            )
        RecipeIngredient.objects.create(
            recipe=cls.r_with_hated, ingredient=cls.i_hated, amount=1, importance=Importance.SECONDARY
        )

        UserTastePreference.objects.create(user=cls.user, ingredient=cls.i_hated, score=TasteLevels.HATE)
        UserCuisinePreference.objects.create(user=cls.user, cuisine=cls.cuisine_hated, score=TasteLevels.HATE)

    def _titles(self, user=None, use_tastes=True):
        qs = RecipeSearchORM.find_recipes(
            {"ingredient": Ingredient.objects.filter(id=self.i_a.id), "use_tastes": use_tastes},
            user=user,
        )
        return set(
            qs.filter(id__in=[self.r_clean.id, self.r_with_hated.id, self.r_hated_cuisine.id])
            .values_list("title", flat=True)
        )

    def test_hated_ingredient_and_cuisine_are_excluded_for_owner(self):
        self.assertEqual(self._titles(user=self.user), {self.r_clean.title})

    def test_use_tastes_off_disables_the_filter(self):
        self.assertEqual(
            self._titles(user=self.user, use_tastes=False),
            {self.r_clean.title, self.r_with_hated.title, self.r_hated_cuisine.title},
        )

    def test_anonymous_search_is_unfiltered(self):
        self.assertEqual(
            self._titles(user=None),
            {self.r_clean.title, self.r_with_hated.title, self.r_hated_cuisine.title},
        )