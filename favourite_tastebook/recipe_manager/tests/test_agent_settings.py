import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from recipe_manager.application.use_cases.agent_chat import AgentChatUseCase
from recipe_manager.application.use_cases.agent_settings import AgentSettingsUseCase
from recipe_manager.application.use_cases.agent_tools import AgentToolsUseCase
from recipe_manager.domain.enums import AgentRecipeSource, TasteLevels
from recipe_manager.domain.exceptions import AgentPayloadError
from recipe_manager.infrastructure.agent import AgentDraftStore
from recipe_manager.infrastructure.selectors import AgentPreferenceSelector
from recipe_manager.models import (
    AgentPreference,
    GeneratedRecipe,
    Ingredient,
    Recipe,
    UserTastePreference,
)

LOCAL_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "agent-settings-tests"}
}


class AgentPreferenceDefaultsTests(TestCase):
    """A user who never opened the panel, and a guest who cannot."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_defaults__", password="x")

    def test_no_row_reads_as_the_defaults(self):
        self.assertEqual(
            AgentPreferenceSelector.for_user(self.user),
            {"use_tastes": True, "recipe_source": AgentRecipeSource.DATABASE, "autosave_drafts": False},
        )

    def test_reading_does_not_create_a_row(self):
        # Opening the studio must stay a read: a row per curious visitor is a
        # table that grows for nothing.
        AgentPreferenceSelector.for_user(self.user)

        self.assertFalse(AgentPreference.objects.filter(user=self.user).exists())

    def test_a_guest_reads_the_same_defaults(self):
        self.assertEqual(
            AgentPreferenceSelector.for_user(None),
            {"use_tastes": True, "recipe_source": AgentRecipeSource.DATABASE, "autosave_drafts": False},
        )


class AgentSettingsUseCaseTests(TestCase):
    """Partial updates, and the values that are refused."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_update__", password="x")

    def test_first_change_creates_the_row(self):
        stored = AgentSettingsUseCase.update(self.user, {"use_tastes": False})

        self.assertFalse(stored["use_tastes"])
        self.assertTrue(AgentPreference.objects.filter(user=self.user).exists())

    def test_an_absent_field_keeps_its_value(self):
        AgentSettingsUseCase.update(self.user, {"autosave_drafts": True})

        stored = AgentSettingsUseCase.update(self.user, {"use_tastes": False})

        # Two switches flipped in two tabs must not undo each other.
        self.assertTrue(stored["autosave_drafts"])
        self.assertFalse(stored["use_tastes"])

    def test_source_takes_the_two_known_words(self):
        stored = AgentSettingsUseCase.update(self.user, {"recipe_source": "ai"})

        self.assertEqual(stored["recipe_source"], AgentRecipeSource.AI)

    def test_an_unknown_source_is_refused(self):
        with self.assertRaises(AgentPayloadError):
            AgentSettingsUseCase.update(self.user, {"recipe_source": "wikipedia"})

    def test_a_non_boolean_is_refused(self):
        with self.assertRaises(AgentPayloadError):
            AgentSettingsUseCase.update(self.user, {"use_tastes": "sometimes"})

    def test_a_form_style_string_is_accepted(self):
        stored = AgentSettingsUseCase.update(self.user, {"autosave_drafts": "true"})

        self.assertTrue(stored["autosave_drafts"])

    def test_an_unknown_key_alone_is_refused(self):
        # Nothing to store, so nothing pretends to have been stored.
        with self.assertRaises(AgentPayloadError):
            AgentSettingsUseCase.update(self.user, {"colour": "red"})

    def test_an_unknown_key_beside_a_known_one_is_ignored(self):
        stored = AgentSettingsUseCase.update(self.user, {"use_tastes": False, "colour": "red"})

        self.assertFalse(stored["use_tastes"])


class AgentSettingsEndpointTests(TestCase):
    """The two calls the gear button makes."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_view__", password="pw")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("agent_settings")

    def test_get_answers_the_defaults(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["settings"]["recipe_source"], AgentRecipeSource.DATABASE)

    def test_post_stores_one_switch(self):
        response = self.client.post(
            self.url, data=json.dumps({"autosave_drafts": True}), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["settings"]["autosave_drafts"])

    def test_a_refused_value_answers_400(self):
        response = self.client.post(
            self.url, data=json.dumps({"recipe_source": "nowhere"}), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_malformed_body_answers_400(self):
        response = self.client.post(self.url, data="not json", content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_a_signed_out_caller_gets_json_not_a_redirect(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "auth_required")


class TasteSwitchTests(TestCase):
    """What the `user_tastes` tool answers once personalisation is off."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_tastes__", password="x")
        cls.loved = Ingredient.objects.create(name="__ut_pref_garlic__", category="vegetable")
        cls.hated = Ingredient.objects.create(name="__ut_pref_liver__", category="meat")
        UserTastePreference.objects.create(user=cls.user, ingredient=cls.loved, score=TasteLevels.LOVE)
        UserTastePreference.objects.create(user=cls.user, ingredient=cls.hated, score=TasteLevels.HATE)

    def test_on_by_default(self):
        result = AgentToolsUseCase.user_tastes({}, user=self.user)

        self.assertTrue(result["tastes_enabled"])
        self.assertIn(self.loved.name, result["loved"])

    def test_off_withholds_the_preferences(self):
        AgentSettingsUseCase.update(self.user, {"use_tastes": False})

        result = AgentToolsUseCase.user_tastes({}, user=self.user)

        self.assertFalse(result["tastes_enabled"])
        self.assertEqual(result["loved"], [])
        self.assertEqual(result["liked"], [])
        self.assertEqual(result["disliked"], [])

    def test_off_still_carries_the_hard_exclusions(self):
        # never_use is where an allergy is recorded, and the save path rejects
        # those ingredients whatever this switch says. Hiding them here would
        # only produce dishes that cannot be kept.
        AgentSettingsUseCase.update(self.user, {"use_tastes": False})

        result = AgentToolsUseCase.user_tastes({}, user=self.user)

        self.assertEqual(result["never_use"], [self.hated.name])

    def test_a_guest_is_unaffected(self):
        result = AgentToolsUseCase.user_tastes({}, user=None)

        self.assertFalse(result["authenticated"])
        self.assertTrue(result["tastes_enabled"])


class RecipeSourceSwitchTests(TestCase):
    """What the catalogue tools answer once the user asked for composed dishes."""

    SEARCH = "recipe_manager.application.use_cases.agent_tools.SearchRecipesUseCase.execute"

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_source__", password="x")

    def test_the_catalogue_is_available_by_default(self):
        # The default is the permissive value: switching nothing must not take
        # away a tool the agent could always call.
        with patch(self.SEARCH, return_value=Recipe.objects.none()) as search:
            result = AgentToolsUseCase.search_recipes({"query": "soup"}, user=self.user)

        self.assertTrue(result["ok"])
        self.assertTrue(search.called)

    def test_ai_only_refuses_the_search_tool(self):
        AgentSettingsUseCase.update(self.user, {"recipe_source": "ai"})

        with patch(self.SEARCH) as search:
            result = AgentToolsUseCase.search_recipes({"query": "soup"}, user=self.user)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "database_search_disabled")
        # Refused, not merely discouraged: the query never reaches the engine.
        self.assertFalse(search.called)
        # And the agent is told what to do instead, or it retries the same call.
        self.assertIn("propose_recipe", result["hint"])

    def test_ai_only_refuses_the_pantry_tool_too(self):
        AgentSettingsUseCase.update(self.user, {"recipe_source": "ai"})

        result = AgentToolsUseCase.recipes_by_ingredients({"ingredients": ["rice"]}, user=self.user)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "database_search_disabled")

    def test_the_refusal_comes_before_the_arguments_are_read(self):
        # A refused tool must not also complain about a missing `query`: the
        # agent would then set about fixing the wrong thing.
        AgentSettingsUseCase.update(self.user, {"recipe_source": "ai"})

        result = AgentToolsUseCase.search_recipes({}, user=self.user)

        self.assertEqual(result["error"], "database_search_disabled")

    def test_composing_is_never_switched_off(self):
        # Whichever way the switch stands, the studio's own reason to exist has
        # to keep working.
        AgentSettingsUseCase.update(self.user, {"recipe_source": "ai"})

        result = AgentToolsUseCase.ingredient_catalog({}, user=self.user)

        self.assertTrue(result["ok"])


@override_settings(CACHES=LOCAL_CACHE)
class AutosaveSwitchTests(TestCase):
    """
    The switch that decides whether the assistant may put a dish away itself.

    It was reported as doing nothing, and it was doing nothing twice over: the
    tool saved whatever the model asked it to, and the page only reacted to the
    other of the two ways a recipe arrives.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_autosave__", password="x")
        cls.chicken = Ingredient.objects.create(name="__ut_auto_chicken__", category="__ut_auto_cat__")

    def setUp(self):
        # The tools write the proposal and the save into the cache; the real one
        # is Redis and is shared between runs.
        cache.clear()

    def _payload(self, title="Autosave Pilaf"):
        return {
            "title": title,
            "cuisine": "uzbek",
            "cook_time_minutes": 30,
            "steps": ["Fry it."],
            "ingredients": [
                {"name": self.chicken.name, "amount": 400, "unit": "g", "importance": "required"}
            ],
        }

    def test_off_by_default_the_agent_may_not_save(self):
        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user, session_id="s")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "autosave_disabled")

    def test_nothing_is_written_when_it_refuses(self):
        AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user, session_id="s")

        self.assertFalse(GeneratedRecipe.objects.filter(user=self.user).exists())

    def test_the_refusal_sends_the_agent_to_propose_instead(self):
        # A bare refusal is what makes a model retry the same call; the person
        # would then get nothing at all rather than a card they can act on.
        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user, session_id="s")

        self.assertIn("propose_recipe", result["hint"])

    def test_proposing_is_never_blocked_by_it(self):
        # The switch governs saving, not composing: refusing both would leave
        # the studio with nothing to show.
        result = AgentToolsUseCase.propose_recipe(self._payload(), user=self.user, session_id="s")

        self.assertTrue(result["ok"])

    def test_on_lets_the_save_through(self):
        AgentSettingsUseCase.update(self.user, {"autosave_drafts": True})

        result = AgentToolsUseCase.save_generated_recipe(self._payload(), user=self.user, session_id="s")

        self.assertTrue(result["ok"])
        self.assertTrue(GeneratedRecipe.objects.filter(user=self.user).exists())


@override_settings(CACHES=LOCAL_CACHE)
class ChatTurnCarriesTheSettingsTests(TestCase):
    """The turn tells the page and the workflow what is switched on."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_turn__", password="x")

    def setUp(self):
        cache.clear()

    class _Client:
        def __init__(self, draft=None, saved=None):
            self.draft = draft
            self.saved = saved
            self.calls = []

        def ask(self, message, context, sid, preferences=None):
            self.calls.append(preferences)
            if self.draft is not None:
                AgentDraftStore.put(sid, self.draft)
            if self.saved is not None:
                AgentDraftStore.put_saved(sid, self.saved)
            return "Here you go."

    def test_the_workflow_receives_them(self):
        AgentSettingsUseCase.update(self.user, {"use_tastes": False})
        fake = self._Client()

        AgentChatUseCase.send(self.user, self.client.session, "hi", client=fake)

        self.assertFalse(fake.calls[0]["use_tastes"])

    def test_autoload_is_off_while_the_switch_is(self):
        fake = self._Client(draft={"title": "Pilaf"})

        result = AgentChatUseCase.send(self.user, self.client.session, "cook", client=fake)

        self.assertIsNotNone(result["draft"])
        self.assertFalse(result["autoload_draft"])

    def test_autoload_follows_the_switch(self):
        AgentSettingsUseCase.update(self.user, {"autosave_drafts": True})
        fake = self._Client(draft={"title": "Pilaf"})

        result = AgentChatUseCase.send(self.user, self.client.session, "cook", client=fake)

        self.assertTrue(result["autoload_draft"])

    def test_autoload_covers_a_dish_the_agent_saved_itself(self):
        # This is the path that actually happens: the assistant reaches for
        # save_generated_recipe far more readily than for propose_recipe, and
        # leaving it out was why the switch looked dead.
        AgentSettingsUseCase.update(self.user, {"autosave_drafts": True})
        fake = self._Client(saved={"id": 7, "title": "Pilaf"})

        result = AgentChatUseCase.send(self.user, self.client.session, "cook", client=fake)

        self.assertIsNone(result["draft"])
        self.assertIsNotNone(result["saved"])
        self.assertTrue(result["autoload_draft"])

    def test_a_saved_dish_does_not_autoload_while_the_switch_is_off(self):
        fake = self._Client(saved={"id": 7, "title": "Pilaf"})

        result = AgentChatUseCase.send(self.user, self.client.session, "cook", client=fake)

        self.assertFalse(result["autoload_draft"])

    def test_a_turn_without_a_draft_never_asks_the_page_to_load_one(self):
        AgentSettingsUseCase.update(self.user, {"autosave_drafts": True})
        fake = self._Client()

        result = AgentChatUseCase.send(self.user, self.client.session, "hello", client=fake)

        self.assertIsNone(result["draft"])
        self.assertFalse(result["autoload_draft"])


class StudioPageShipsTheSettingsTests(TestCase):
    """The panel renders from the page, not from a fetch on open."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_prefs_page__", password="pw")

    def test_the_context_carries_them(self):
        AgentSettingsUseCase.update(self.user, {"recipe_source": "ai"})
        self.client.force_login(self.user)

        response = self.client.get(reverse("recipe_studio"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["agent_settings"]["recipe_source"], AgentRecipeSource.AI)
