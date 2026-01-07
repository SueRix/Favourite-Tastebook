from django.test import TestCase

from recipe_manager.domain.enums import Importance
from recipe_manager.models import Cuisine, Ingredient, Recipe, RecipeIngredient
from recipe_manager.services.recipe_selection_service import annotate_recipe_scores


class RecipeSelectionServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cuisine = Cuisine.objects.create(name="__ut_cuisine_selection__")

        cls.i_a = Ingredient.objects.create(name="__ut_ing_a__", category="__ut_cat__")
        cls.i_b = Ingredient.objects.create(name="__ut_ing_b__", category="__ut_cat__")
        cls.i_c = Ingredient.objects.create(name="__ut_ing_c__", category="__ut_cat__")

        cls.r1 = Recipe.objects.create(title="__ut_recipe_r1__", cook_time=10, cuisine=cls.cuisine)
        cls.r2 = Recipe.objects.create(title="__ut_recipe_r2__", cook_time=20, cuisine=cls.cuisine)

        RecipeIngredient.objects.create(recipe=cls.r1, ingredient=cls.i_a, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r1, ingredient=cls.i_b, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r1, ingredient=cls.i_c, amount=1, importance=Importance.OPTIONAL)

        RecipeIngredient.objects.create(recipe=cls.r2, ingredient=cls.i_a, amount=1, importance=Importance.REQUIRED)
        RecipeIngredient.objects.create(recipe=cls.r2, ingredient=cls.i_c, amount=1, importance=Importance.SECONDARY)

    def _annotated_qs(self, selected_ids, weights=None):
        return annotate_recipe_scores(
            qs=Recipe.objects.all(),
            selected_ids=selected_ids,
            weights=weights,
        )

    def _assert_fields(self, obj, expected: dict[str, int]):
        for field, value in expected.items():
            with self.subTest(obj_id=obj.id, field=field):
                self.assertEqual(getattr(obj, field), value)

    def test_annotate_sets_expected_counters(self):
        qs = self._annotated_qs(selected_ids=[self.i_a.id, self.i_c.id])
        r1 = qs.get(id=self.r1.id)
        r2 = qs.get(id=self.r2.id)

        self._assert_fields(
            r1,
            {
                "required_total": 2,
                "required_matched": 1,
                "optional_matched": 1,
                "secondary_matched": 0,
                "total_matches": 2,
                "missing_required": 1,
            },
        )
        self._assert_fields(
            r2,
            {
                "required_total": 1,
                "required_matched": 1,
                "secondary_matched": 1,
                "optional_matched": 0,
                "total_matches": 2,
                "missing_required": 0,
            },
        )

    def test_annotate_score_orders_reasonably(self):
        qs = (
            self._annotated_qs(selected_ids=[self.i_a.id, self.i_c.id])
            .filter(id__in=[self.r1.id, self.r2.id])
            .order_by("-score")
        )
        self.assertEqual(qs.first().id, self.r2.id)

    def test_annotate_accepts_weight_override(self):
        qs = (
            self._annotated_qs(
                selected_ids=[self.i_a.id, self.i_c.id],
                weights={"missing_required_match": 9999},
            )
            .filter(id__in=[self.r1.id, self.r2.id])
            .order_by("-score")
        )
        self.assertEqual(qs.first().id, self.r2.id)
