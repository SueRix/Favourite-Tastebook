import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from recipe_manager.application.use_cases.agent_chat import AgentChatUseCase
from recipe_manager.application.use_cases.agent_settings import AgentSettingsUseCase
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

        def ask(self, message, context, sid, preferences=None):
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


@override_settings(CACHES=LOCAL_CACHE)
class RecipeStudioPreviewTests(TestCase):
    """Looking at the draft as a recipe card, without keeping it."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_prev__", password="secret123")
        cls.chicken = Ingredient.objects.create(name="__ut_prev_chicken__", category="__ut_prev_cat__")
        cls.rice = Ingredient.objects.create(name="__ut_prev_rice__", category="__ut_prev_cat__")

    def setUp(self):
        cache.clear()
        self.url = reverse("recipe_studio_preview")

    def _post(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def _login(self):
        self.client.login(username="__ut_studio_prev__", password="secret123")

    def test_it_renders_the_card_every_other_page_renders(self):
        # The point of the endpoint: one template for the catalogue card and the
        # draft card, so the preview cannot drift away from the real thing.
        self._login()
        response = self._post(draft_payload(self.chicken.name, self.rice.name))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/recipe_database_card_modal.html")
        self.assertContains(response, "Studio Pilaf")
        self.assertContains(response, self.chicken.name)
        self.assertContains(response, "Fry the chicken.")

    def test_previewing_stores_nothing(self):
        self._login()
        self._post(draft_payload(self.chicken.name, self.rice.name))

        self.assertFalse(GeneratedRecipe.objects.exists())

    def test_the_card_carries_no_controls_that_need_a_recipe_id(self):
        # Like, dislike and save all address a recipe by id, and a draft has
        # none. The buttons would act on whatever id they were given.
        self._login()
        response = self._post(draft_payload(self.chicken.name, self.rice.name))

        self.assertNotContains(response, "toggleTasteAction")
        self.assertNotContains(response, "toggleFavorite")

    def test_a_half_written_draft_can_still_be_looked_at(self):
        # Nothing is being created, so the checks that refuse a save do not
        # apply: no title, no steps and no ingredients is a legitimate draft.
        self._login()
        response = self._post({"title": "", "steps": [], "ingredients": []})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No ingredients data.")

    def test_an_ingredient_the_catalogue_does_not_know_is_shown_not_refused(self):
        # The editor already says so on the row, and the save says so again.
        self._login()
        response = self._post(draft_payload(self.chicken.name, "__ut_prev_yuzu__"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "__ut_prev_yuzu__")

    def test_the_picture_lands_where_a_catalogue_photo_would(self):
        self._login()
        payload = draft_payload(
            self.chicken.name, self.rice.name, image_url="https://example.test/dish.jpg"
        )

        response = self._post(payload)

        self.assertContains(response, "https://example.test/dish.jpg")
        self.assertNotContains(response, "No photo available")

    def test_without_a_picture_the_card_says_so(self):
        self._login()
        response = self._post(draft_payload(self.chicken.name, self.rice.name))

        self.assertContains(response, "No photo available")

    def test_something_that_is_not_a_link_is_refused_with_a_readable_reason(self):
        # It ends up in an <img src>; "example.com/x.jpg" renders as a broken
        # image, and javascript: has no business being there at all.
        self._login()
        response = self._post(
            draft_payload(self.chicken.name, self.rice.name, image_url="javascript:alert(1)")
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("image_url", json.loads(response.content)["detail"])

    def test_malformed_body_is_a_400(self):
        self._login()
        response = self.client.post(self.url, data="not json", content_type="application/json")

        self.assertEqual(response.status_code, 400)

    def test_guest_gets_json_401(self):
        response = self._post(draft_payload(self.chicken.name, self.rice.name))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"], "auth_required")


@override_settings(CACHES=LOCAL_CACHE)
class GeneratedRecipeImageTests(TestCase):
    """The picture a generated dish will eventually get."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_img__", password="secret123")
        cls.chicken = Ingredient.objects.create(name="__ut_img_chicken__", category="__ut_img_cat__")
        cls.rice = Ingredient.objects.create(name="__ut_img_rice__", category="__ut_img_cat__")

    def setUp(self):
        cache.clear()

    def _login(self):
        self.client.login(username="__ut_studio_img__", password="secret123")

    def test_a_saved_draft_keeps_its_link(self):
        self._login()
        payload = draft_payload(
            self.chicken.name, self.rice.name, image_url="https://example.test/pilaf.jpg"
        )

        self.client.post(
            reverse("recipe_studio_save"), data=json.dumps(payload), content_type="application/json"
        )

        recipe = GeneratedRecipe.objects.get(user=self.user)
        self.assertEqual(recipe.image_url, "https://example.test/pilaf.jpg")

    def test_no_link_is_the_normal_answer(self):
        # Until an image model fills it in, every recipe saved here has none —
        # and that must not be an error.
        self._login()

        response = self.client.post(
            reverse("recipe_studio_save"),
            data=json.dumps(draft_payload(self.chicken.name, self.rice.name)),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(GeneratedRecipe.objects.get(user=self.user).image_url, "")

    def test_a_stored_creation_comes_back_to_the_editor_with_it(self):
        self._login()
        recipe = GeneratedRecipe.objects.create(
            user=self.user,
            title="Photographed",
            cook_time=20,
            steps=["Do it."],
            image_url="https://example.test/one.jpg",
        )
        recipe.ingredients.create(ingredient=self.chicken, amount=1, unit="pcs")

        response = self.client.get(reverse("recipe_studio_creations"))

        recipes = json.loads(response.content)["recipes"]
        self.assertEqual(recipes[0]["image_url"], "https://example.test/one.jpg")


@override_settings(CACHES=LOCAL_CACHE)
class AgentSaveReachesThePageTests(TestCase):
    """
    A dish the agent stores itself has to appear without a reload.

    The save happens on a tool call the browser never sees, so the only way the
    page can learn about it is the same join the proposal uses: the tool leaves
    the stored recipe under the conversation id, the chat turn picks it up.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_ann__", password="x")
        cls.chicken = Ingredient.objects.create(name="__ut_ann_chicken__", category="__ut_ann_cat__")
        cls.rice = Ingredient.objects.create(name="__ut_ann_rice__", category="__ut_ann_cat__")
        # The agent may only save for a user who allowed it to.
        AgentSettingsUseCase.update(cls.user, {"autosave_drafts": True})

    def setUp(self):
        cache.clear()

    def test_the_tool_leaves_the_saved_recipe_for_the_chat_view(self):
        AgentToolsUseCase.save_generated_recipe(
            draft_payload(self.chicken.name, self.rice.name), user=self.user, session_id="sid-1"
        )

        announced = AgentDraftStore.take_saved("sid-1")
        self.assertEqual(announced["title"], "Studio Pilaf")
        # The editable shape, so opening it in the editor needs no special case.
        self.assertEqual(announced["ingredients"][0]["name"], self.chicken.name)
        self.assertIsNotNone(announced["id"])

    def test_a_save_is_not_a_proposal(self):
        # The two slots must not bleed into each other: a stored dish printed as
        # a proposal would offer to save it a second time.
        AgentToolsUseCase.save_generated_recipe(
            draft_payload(self.chicken.name, self.rice.name), user=self.user, session_id="sid-1"
        )

        self.assertIsNone(AgentDraftStore.take("sid-1"))

    def test_a_refused_save_announces_nothing(self):
        AgentToolsUseCase.save_generated_recipe(
            draft_payload(self.chicken.name, "__ut_ann_yuzu__"), user=self.user, session_id="sid-1"
        )

        self.assertIsNone(AgentDraftStore.take_saved("sid-1"))

    def test_the_chat_turn_carries_it(self):
        recipe = {"id": 7, "title": "Saved By The Agent"}

        class _Client:
            def ask(self, message, context, sid, preferences=None):
                AgentDraftStore.put_saved(sid, recipe)
                return "Kept it for you."

        result = AgentChatUseCase.send(self.user, self.client.session, "save it", client=_Client())

        self.assertEqual(result["saved"], recipe)
        self.assertIsNone(result["draft"])

    def test_a_quiet_turn_carries_nothing(self):
        class _Client:
            def ask(self, message, context, sid, preferences=None):
                return "Just talking."

        result = AgentChatUseCase.send(self.user, self.client.session, "hello", client=_Client())

        self.assertIsNone(result["saved"])


@override_settings(CACHES=LOCAL_CACHE)
class RecipeStudioCreationsEndpointTests(TestCase):
    """The list the page re-reads after every write."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_list__", password="secret123")
        cls.other = get_user_model().objects.create_user(username="__ut_studio_list2__", password="x")
        cls.chicken = Ingredient.objects.create(name="__ut_list_chicken__", category="__ut_list_cat__")

    def setUp(self):
        cache.clear()
        self.url = reverse("recipe_studio_creations")

    def test_it_answers_with_the_editable_shape(self):
        recipe = GeneratedRecipe.objects.create(
            user=self.user, title="Listed One", cook_time=15, steps=["Do it."]
        )
        recipe.ingredients.create(ingredient=self.chicken, amount=1, unit="pcs")
        self.client.login(username="__ut_studio_list__", password="secret123")

        response = self.client.get(self.url)
        recipes = json.loads(response.content)["recipes"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(recipes[0]["title"], "Listed One")
        self.assertEqual(recipes[0]["ingredients"][0]["name"], self.chicken.name)

    def test_a_save_is_visible_on_the_next_read(self):
        # The whole point of the endpoint: no reload, no stale copy on screen.
        self.client.login(username="__ut_studio_list__", password="secret123")
        self.assertEqual(json.loads(self.client.get(self.url).content)["recipes"], [])

        GeneratedRecipe.objects.create(user=self.user, title="Fresh", cook_time=5, steps=["x"])

        self.assertEqual(len(json.loads(self.client.get(self.url).content)["recipes"]), 1)

    def test_it_shows_no_recipes_belonging_to_anybody_else(self):
        GeneratedRecipe.objects.create(user=self.other, title="Theirs", cook_time=10, steps=["x"])
        self.client.login(username="__ut_studio_list__", password="secret123")

        self.assertEqual(json.loads(self.client.get(self.url).content)["recipes"], [])

    def test_guest_gets_json_401(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"], "auth_required")


@override_settings(CACHES=LOCAL_CACHE)
class RecipeStudioDeleteTests(TestCase):
    """Dropping a creation - the one write the agent may not perform."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_studio_del__", password="secret123")
        cls.other = get_user_model().objects.create_user(username="__ut_studio_del2__", password="x")
        cls.chicken = Ingredient.objects.create(name="__ut_del_chicken__", category="__ut_del_cat__")

    def setUp(self):
        cache.clear()

    def _url(self, recipe_id):
        return reverse("recipe_studio_creation_delete", args=[recipe_id])

    def _creation(self, user, title="Delete Me"):
        recipe = GeneratedRecipe.objects.create(user=user, title=title, cook_time=10, steps=["x"])
        recipe.ingredients.create(ingredient=self.chicken, amount=1, unit="pcs")
        return recipe

    def test_the_owner_can_delete_it(self):
        recipe = self._creation(self.user)
        self.client.login(username="__ut_studio_del__", password="secret123")

        response = self.client.delete(self._url(recipe.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["title"], "Delete Me")
        self.assertFalse(GeneratedRecipe.objects.filter(id=recipe.id).exists())

    def test_the_ingredient_lines_go_with_it_and_the_catalogue_stays(self):
        recipe = self._creation(self.user)
        self.client.login(username="__ut_studio_del__", password="secret123")

        self.client.delete(self._url(recipe.id))

        self.assertFalse(recipe.ingredients.exists())
        # Ingredient rows are shared catalogue data, not a recipe's to take away.
        self.assertTrue(Ingredient.objects.filter(id=self.chicken.id).exists())

    def test_a_recipe_owned_by_another_user_is_a_404_and_survives(self):
        recipe = self._creation(self.other, title="Theirs")
        self.client.login(username="__ut_studio_del__", password="secret123")

        response = self.client.delete(self._url(recipe.id))

        # Indistinguishable from an id that never existed: the endpoint is not a
        # way to find out which ids are real.
        self.assertEqual(response.status_code, 404)
        self.assertTrue(GeneratedRecipe.objects.filter(id=recipe.id).exists())

    def test_an_unknown_id_is_a_404(self):
        self.client.login(username="__ut_studio_del__", password="secret123")

        self.assertEqual(self.client.delete(self._url(9999999)).status_code, 404)

    def test_guest_gets_json_401(self):
        recipe = self._creation(self.user)

        response = self.client.delete(self._url(recipe.id))

        self.assertEqual(response.status_code, 401)
        self.assertTrue(GeneratedRecipe.objects.filter(id=recipe.id).exists())
