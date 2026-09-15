from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from recipe_manager.application.use_cases.agent_settings import AgentSettingsUseCase
from recipe_manager.application.use_cases.agent_tools import AgentToolsUseCase
from recipe_manager.domain.enums import Importance, TasteLevels, Units
from recipe_manager.domain.exceptions import AgentPayloadError
from recipe_manager.models import GeneratedRecipe, Ingredient, UserTastePreference


class SaveGeneratedRecipeToolTests(TestCase):
    """
    Covers the tool the cooking agent uses to keep a dish it composed itself.

    The point of these tests is the boundary between invented text and stored
    data: only known ingredients get through, and the user's never_use list is
    enforced by the server rather than by the system prompt.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="__ut_gen_user__", password="x"
        )
        # Saving on the user's behalf is off by default; these tests are about
        # what the tool does once it is allowed to run at all.
        AgentSettingsUseCase.update(cls.user, {"autosave_drafts": True})
        cls.chicken = Ingredient.objects.create(name="__ut_gen_chicken__", category="__ut_gen_cat__")
        cls.rice = Ingredient.objects.create(name="__ut_gen_rice__", category="__ut_gen_cat__")
        cls.bread = Ingredient.objects.create(name="__ut_gen_bread__", category="__ut_gen_cat__")

    def _payload(self, **overrides):
        payload = {
            "title": "Agent Pilaf",
            "cuisine": "uzbek",
            "cook_time_minutes": 45,
            "steps": ["Fry the chicken.", "Add rice and water.", "Simmer 20 minutes."],
            "ingredients": [
                {"name": self.chicken.name, "amount": 400, "unit": "g", "importance": "required"},
                {"name": self.rice.name, "amount": 300, "unit": "g", "importance": "required"},
            ],
        }
        payload.update(overrides)
        return payload

    def test_saves_recipe_with_linked_ingredients(self):
        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user)

        self.assertTrue(result["ok"])
        self.assertFalse(result["already_saved"])

        recipe = GeneratedRecipe.objects.get(user=self.user, title="Agent Pilaf")
        self.assertEqual(recipe.cook_time, 45)
        self.assertEqual(len(recipe.steps), 3)
        self.assertEqual(
            sorted(recipe.ingredients.values_list("ingredient__name", flat=True)),
            sorted([self.chicken.name, self.rice.name]),
        )
        # The echo back carries the stored form, not the draft the agent sent.
        self.assertEqual(result["recipe"]["ingredients"]["required"][0]["unit"], Units.GRAM)

    def test_unknown_ingredient_is_reported_with_names(self):
        payload = self._payload(ingredients=[
            {"name": self.chicken.name, "amount": 1, "unit": "pcs"},
            {"name": "__ut_gen_saffron_we_lack__", "amount": 1, "unit": "pinch"},
        ])

        result = AgentToolsUseCase.save_generated_recipe(payload, user=self.user)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "unknown_ingredients")
        self.assertEqual(result["unknown"], ["__ut_gen_saffron_we_lack__"])
        self.assertFalse(GeneratedRecipe.objects.filter(user=self.user).exists())

    def test_never_use_ingredient_is_refused_by_the_server(self):
        UserTastePreference.objects.create(
            user=self.user, ingredient=self.bread, score=TasteLevels.HATE
        )
        payload = self._payload(ingredients=[
            {"name": self.chicken.name, "amount": 1, "unit": "pcs"},
            {"name": self.bread.name, "amount": 2, "unit": "pcs"},
        ])

        result = AgentToolsUseCase.save_generated_recipe(payload, user=self.user)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "taboo_ingredient")
        self.assertEqual(result["ingredients"], [self.bread.name])
        self.assertFalse(GeneratedRecipe.objects.filter(user=self.user).exists())

    def test_disliked_ingredient_is_allowed(self):
        # Only HATE is a hard exclusion; a dislike is a preference to weigh.
        UserTastePreference.objects.create(
            user=self.user, ingredient=self.rice, score=TasteLevels.DISLIKE
        )
        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user)
        self.assertTrue(result["ok"])

    def test_same_title_twice_is_idempotent(self):
        AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user)
        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user)

        self.assertTrue(result["ok"])
        self.assertTrue(result["already_saved"])
        self.assertEqual(GeneratedRecipe.objects.filter(user=self.user).count(), 1)

    def test_another_user_may_keep_the_same_title(self):
        other = get_user_model().objects.create_user(username="__ut_gen_other__", password="x")
        AgentSettingsUseCase.update(other, {"autosave_drafts": True})
        AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user)
        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=other)

        self.assertTrue(result["ok"])
        self.assertFalse(result["already_saved"])

    def test_repeated_ingredient_does_not_break_the_save(self):
        payload = self._payload(ingredients=[
            {"name": self.chicken.name, "amount": 400, "unit": "g"},
            {"name": self.chicken.name, "amount": 100, "unit": "g"},
        ])
        result = AgentToolsUseCase.save_generated_recipe(payload, user=self.user)

        self.assertTrue(result["ok"])
        recipe = GeneratedRecipe.objects.get(user=self.user)
        self.assertEqual(recipe.ingredients.count(), 1)

    def test_amount_is_clamped_to_what_the_column_holds(self):
        payload = self._payload(ingredients=[
            {"name": self.chicken.name, "amount": 10 ** 9, "unit": "g"},
        ])
        AgentToolsUseCase.save_generated_recipe(payload, user=self.user)

        line = GeneratedRecipe.objects.get(user=self.user).ingredients.first()
        self.assertEqual(line.amount, Decimal("9999.99"))

    def test_unit_outside_the_vocabulary_is_rejected(self):
        payload = self._payload(ingredients=[
            {"name": self.chicken.name, "amount": 1, "unit": "handful"},
        ])
        with self.assertRaises(AgentPayloadError):
            AgentToolsUseCase.save_generated_recipe(payload, user=self.user)

    def test_guest_cannot_save(self):
        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=None)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "auth_required")
        self.assertFalse(GeneratedRecipe.objects.exists())

    def test_steps_sent_as_one_blob_are_split(self):
        payload = self._payload(steps="First step.\nSecond step.")
        AgentToolsUseCase.save_generated_recipe(payload, user=self.user)

        self.assertEqual(
            GeneratedRecipe.objects.get(user=self.user).steps,
            ["First step.", "Second step."],
        )

    def test_ingredients_sent_as_a_json_string_are_parsed(self):
        # Models routinely hand a nested array over still serialised.
        payload = self._payload(ingredients=(
            '[{"name": "%s", "amount": 400, "unit": "g"}]' % self.chicken.name
        ))
        result = AgentToolsUseCase.save_generated_recipe(payload, user=self.user)

        self.assertTrue(result["ok"])
        self.assertEqual(GeneratedRecipe.objects.get(user=self.user).ingredients.count(), 1)


class IngredientCatalogToolTests(TestCase):
    """The vocabulary the agent must compose from."""

    @classmethod
    def setUpTestData(cls):
        Ingredient.objects.create(name="__ut_cat_basil__", category="__ut_cat_herbs__")
        Ingredient.objects.create(name="__ut_cat_thyme__", category="__ut_cat_herbs__")

    def test_returns_names_grouped_by_category(self):
        result = AgentToolsUseCase.ingredient_catalog({}, user=None)

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["ingredients"]["__ut_cat_herbs__"],
            ["__ut_cat_basil__", "__ut_cat_thyme__"],
        )

    def test_exposes_the_units_and_importance_values_the_save_tool_accepts(self):
        result = AgentToolsUseCase.ingredient_catalog({}, user=None)

        self.assertEqual(result["units"], sorted(Units.values))
        self.assertEqual(result["importance"], sorted(Importance.values))
