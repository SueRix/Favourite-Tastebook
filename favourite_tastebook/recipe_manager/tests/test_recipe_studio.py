import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from recipe_manager.application.use_cases.agent_chat import AgentChatUseCase
from recipe_manager.application.use_cases.agent_tools import AgentToolsUseCase
from recipe_manager.domain.enums import TasteLevels
from recipe_manager.infrastructure.agent import AgentDraftStore
from recipe_manager.models import GeneratedRecipe, Ingredient, UserTastePreference

LOCAL_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "studio-tests"}
}


def draft_payload(chicken, rice, **overrides):
    payload = {
        "title": "Studio Pilaf",
        "cuisine": "uzbek",
        "cook_time_minutes": 40,
        "steps": ["Fry the chicken.", "Add the rice."],
        "ingredients": [
            {"name": chicken, "amount": 400, "unit": "g", "importance": "required"},
            {"name": rice, "amount": 300, "unit": "g", "importance": "required"},
        ],
    }
    payload.update(overrides)
    return payload


@override_settings(CACHES=LOCAL_CACHE)
class AgentDraftStoreTests(TestCase):
    """The join between a tool call and the reply that comes back separately."""

    def setUp(self):
        cache.clear()

    def test_put_then_take(self):
        AgentDraftStore.put("sid-1", {"title": "X"})
        self.assertEqual(AgentDraftStore.take("sid-1"), {"title": "X"})

    def test_take_is_one_shot(self):
        # A draft belongs to the turn that produced it; re-delivering it on the
        # next message would overwrite whatever the person had edited on screen.
        AgentDraftStore.put("sid-1", {"title": "X"})
        AgentDraftStore.take("sid-1")

        self.assertIsNone(AgentDraftStore.take("sid-1"))

    def test_conversations_do_not_share_drafts(self):
        AgentDraftStore.put("sid-1", {"title": "mine"})

        self.assertIsNone(AgentDraftStore.take("sid-2"))

    def test_missing_sid_is_survivable(self):
        AgentDraftStore.put("", {"title": "X"})
        self.assertIsNone(AgentDraftStore.take(""))


@override_settings(CACHES=LOCAL_CACHE)
class ProposeRecipeToolTests(TestCase):
    """The tool that offers a dish without committing it."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_prop__", password="x")
        cls.chicken = Ingredient.objects.create(name="__ut_st_chicken__", category="__ut_st_cat__")
        cls.rice = Ingredient.objects.create(name="__ut_st_rice__", category="__ut_st_cat__")
        cls.bread = Ingredient.objects.create(name="__ut_st_bread__", category="__ut_st_cat__")

    def setUp(self):
        cache.clear()

    def test_proposal_is_not_a_save(self):
        result = AgentToolsUseCase.propose_recipe(
            draft_payload(self.chicken.name, self.rice.name), user=self.user, session_id="sid-1"
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["proposed"])
        self.assertFalse(GeneratedRecipe.objects.exists())

    def test_draft_is_left_for_the_chat_view(self):
        AgentToolsUseCase.propose_recipe(
            draft_payload(self.chicken.name, self.rice.name), user=self.user, session_id="sid-1"
        )

        draft = AgentDraftStore.take("sid-1")
        self.assertEqual(draft["title"], "Studio Pilaf")
        self.assertEqual(len(draft["ingredients"]), 2)
        # Flat, not grouped: every line becomes an editable row.
        self.assertEqual(draft["ingredients"][0]["unit"], "g")

    def test_taboo_is_refused_before_anything_is_offered(self):
        UserTastePreference.objects.create(
            user=self.user, ingredient=self.bread, score=TasteLevels.HATE
        )
        payload = draft_payload(self.chicken.name, self.rice.name)
        payload["ingredients"].append({"name": self.bread.name, "amount": 1, "unit": "pcs"})

        result = AgentToolsUseCase.propose_recipe(payload, user=self.user, session_id="sid-1")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "taboo_ingredient")
        self.assertIsNone(AgentDraftStore.take("sid-1"))

    def test_unknown_ingredient_is_refused_with_names(self):
        payload = draft_payload(self.chicken.name, "__ut_st_yuzu_we_lack__")

        result = AgentToolsUseCase.propose_recipe(payload, user=self.user, session_id="sid-1")

        self.assertEqual(result["error"], "unknown_ingredients")
        self.assertEqual(result["unknown"], ["__ut_st_yuzu_we_lack__"])

    def test_guest_cannot_propose(self):
        result = AgentToolsUseCase.propose_recipe(
            draft_payload(self.chicken.name, self.rice.name), user=None, session_id="sid-1"
        )

        self.assertEqual(result["error"], "auth_required")


@override_settings(CACHES=LOCAL_CACHE)
class ChatCarriesTheDraftTests(TestCase):
    """A reply and the draft proposed while producing it arrive together."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_chat__", password="x")

    def setUp(self):
        cache.clear()
        self.session = self.client.session

    class _Client:
        """Stands in for n8n, proposing a draft mid-call the way the agent does."""

        def __init__(self, draft=None):
            self.draft = draft

        def ask(self, message, context, sid):
            if self.draft is not None:
                AgentDraftStore.put(sid, self.draft)
            return "Here you go."

    def test_draft_travels_with_the_reply(self):
        result = AgentChatUseCase.send(
            self.user, self.session, "invent something", client=self._Client({"title": "X"})
        )

        self.assertEqual(result["reply"], "Here you go.")
        self.assertEqual(result["draft"], {"title": "X"})

    def test_no_proposal_means_no_draft(self):
        result = AgentChatUseCase.send(self.user, self.session, "hello", client=self._Client())

        self.assertIsNone(result["draft"])

    def test_a_stale_draft_is_not_re_delivered(self):
        first = AgentChatUseCase.send(
            self.user, self.session, "invent", client=self._Client({"title": "X"})
        )
        second = AgentChatUseCase.send(self.user, self.session, "thanks", client=self._Client())

        self.assertIsNotNone(first["draft"])
        self.assertIsNone(second["draft"])


@override_settings(CACHES=LOCAL_CACHE)
class RecipeStudioPageTests(TestCase):
    """The page itself: who may open it and what it carries."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_page__", password="secret123")
        cls.chicken = Ingredient.objects.create(name="__ut_page_chicken__", category="__ut_page_cat__")

    def setUp(self):
        cache.clear()
        self.url = reverse("recipe_studio")

    def test_guest_is_sent_to_the_login_page(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_page_opens_for_a_signed_in_user(self):
        self.client.login(username="__ut_studio_page__", password="secret123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main/recipe_studio.html")

    def test_page_ships_the_vocabularies_the_editor_needs(self):
        self.client.login(username="__ut_studio_page__", password="secret123")
        response = self.client.get(self.url)

        # Without the catalogue on the page an edited row could name something
        # the save would refuse.
        self.assertIn("__ut_page_cat__", response.context["ingredient_catalog"])
        self.assertIn("g", response.context["units"])
        self.assertIn("required", response.context["importance_levels"])

    def test_past_creations_arrive_in_the_editable_shape(self):
        self.client.login(username="__ut_studio_page__", password="secret123")
        recipe = GeneratedRecipe.objects.create(
            user=self.user, title="Old One", cook_time=15, steps=["Do it."]
        )
        recipe.ingredients.create(ingredient=self.chicken, amount=1, unit="pcs")

        response = self.client.get(self.url)
        creations = response.context["my_recipes"]

        self.assertEqual(len(creations), 1)
        self.assertEqual(creations[0]["title"], "Old One")
        # Same shape as a fresh draft, so the editor needs no special case.
        self.assertEqual(creations[0]["ingredients"][0]["name"], self.chicken.name)

    def test_creations_are_private_to_their_owner(self):
        other = get_user_model().objects.create_user(username="__ut_studio_other__", password="x")
        GeneratedRecipe.objects.create(user=other, title="Theirs", cook_time=10, steps=["x"])

        self.client.login(username="__ut_studio_page__", password="secret123")
        response = self.client.get(self.url)

        self.assertEqual(response.context["my_recipes"], [])


@override_settings(CACHES=LOCAL_CACHE)
class RecipeStudioSaveTests(TestCase):
    """Saving the draft as the person edited it."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_save__", password="secret123")
        cls.chicken = Ingredient.objects.create(name="__ut_save_chicken__", category="__ut_save_cat__")
        cls.rice = Ingredient.objects.create(name="__ut_save_rice__", category="__ut_save_cat__")
        cls.bread = Ingredient.objects.create(name="__ut_save_bread__", category="__ut_save_cat__")

    def setUp(self):
        cache.clear()
        self.url = reverse("recipe_studio_save")

    def _post(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def _login(self):
        self.client.login(username="__ut_studio_save__", password="secret123")

    def test_saves_the_edited_draft(self):
        self._login()
        payload = draft_payload(self.chicken.name, self.rice.name, title="My Own Pilaf")

        response = self._post(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["title"], "My Own Pilaf")
        self.assertTrue(GeneratedRecipe.objects.filter(user=self.user, title="My Own Pilaf").exists())

    def test_edited_units_are_kept(self):
        # The whole reason the draft is editable: the model sends no unit and
        # everything defaults to grams, so "2 g of onion" is fixed by hand.
        self._login()
        payload = draft_payload(self.chicken.name, self.rice.name)
        payload["ingredients"][0]["unit"] = "pcs"

        self._post(payload)

        line = GeneratedRecipe.objects.get(user=self.user).ingredients.get(ingredient=self.chicken)
        self.assertEqual(line.unit, "pcs")

    def test_editing_cannot_smuggle_a_taboo_ingredient_past_the_check(self):
        self._login()
        UserTastePreference.objects.create(
            user=self.user, ingredient=self.bread, score=TasteLevels.HATE
        )
        payload = draft_payload(self.chicken.name, self.rice.name)
        payload["ingredients"].append({"name": self.bread.name, "amount": 1, "unit": "pcs"})

        response = self._post(payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"], "taboo_ingredient")
        self.assertFalse(GeneratedRecipe.objects.exists())

    def test_unknown_ingredient_is_named_back(self):
        self._login()
        response = self._post(draft_payload(self.chicken.name, "__ut_save_yuzu__"))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["unknown"], ["__ut_save_yuzu__"])

    def test_same_title_twice_is_a_conflict(self):
        self._login()
        payload = draft_payload(self.chicken.name, self.rice.name)
        self._post(payload)

        response = self._post(payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(GeneratedRecipe.objects.count(), 1)

    def test_missing_title_is_rejected_with_a_readable_reason(self):
        self._login()
        response = self._post(draft_payload(self.chicken.name, self.rice.name, title=""))

        self.assertEqual(response.status_code, 400)
        self.assertIn("title", json.loads(response.content)["detail"])

    def test_malformed_body_is_a_400(self):
        self._login()
        response = self.client.post(self.url, data="not json", content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_guest_gets_json_401(self):
        response = self._post(draft_payload(self.chicken.name, self.rice.name))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"], "auth_required")
        self.assertFalse(GeneratedRecipe.objects.exists())
