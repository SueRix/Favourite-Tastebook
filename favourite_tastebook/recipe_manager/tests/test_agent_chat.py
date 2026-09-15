import json
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from recipe_manager.application.use_cases.agent_chat import AgentChatUseCase
from recipe_manager.domain.exceptions import (
    AgentChatMessageError,
    AgentChatNotConfiguredError,
    AgentChatRateLimitedError,
    AgentChatResponseError,
    AgentChatUnavailableError,
)
from recipe_manager.infrastructure.agent import AgentContextToken, N8nAgentChatClient

# The real cache is Redis and is shared between runs; the counters under test
# must start empty and must not leak into anything else.
LOCAL_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "agent-chat-tests"}
}


class FakeChatClient:
    """Stands in for the n8n webhook and records what the use case sent it."""

    def __init__(self, reply="Try a pilaf.", error=None):
        self.reply = reply
        self.error = error
        self.calls = []

    def ask(self, message, context, sid, preferences=None):
        self.calls.append(
            {"message": message, "context": context, "sid": sid, "preferences": preferences}
        )
        if self.error:
            raise self.error
        return self.reply


@override_settings(CACHES=LOCAL_CACHE)
class AgentChatUseCaseTests(TestCase):
    """One turn of the conversation, from the browser's message to the reply."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_chat_user__", password="x")

    def setUp(self):
        cache.clear()
        self.session = self.client.session

    def test_sends_message_and_returns_reply(self):
        fake = FakeChatClient()

        result = AgentChatUseCase.send(self.user, self.session, "что приготовить?", client=fake)

        self.assertEqual(result["reply"], "Try a pilaf.")
        self.assertEqual(fake.calls[0]["message"], "что приготовить?")

    def test_user_is_sealed_into_the_signed_context(self):
        fake = FakeChatClient()

        result = AgentChatUseCase.send(self.user, self.session, "hi", client=fake)
        sent = fake.calls[0]

        # The payload carries no user field at all; the identity is in the token.
        # The settings that travel beside it say how the assistant should behave,
        # never whose settings they are.
        self.assertEqual(set(sent), {"message", "context", "sid", "preferences"})
        self.assertEqual(
            AgentContextToken.parse(sent["context"]),
            {"uid": self.user.id, "sid": result["chat_id"]},
        )

    def test_same_session_keeps_one_conversation(self):
        fake = FakeChatClient()

        first = AgentChatUseCase.send(self.user, self.session, "hi", client=fake)
        second = AgentChatUseCase.send(self.user, self.session, "and now?", client=fake)

        self.assertEqual(first["chat_id"], second["chat_id"])

    def test_reset_starts_a_new_conversation(self):
        fake = FakeChatClient()
        first = AgentChatUseCase.send(self.user, self.session, "hi", client=fake)

        AgentChatUseCase.reset(self.session)
        second = AgentChatUseCase.send(self.user, self.session, "hi", client=fake)

        self.assertNotEqual(second["chat_id"], first["chat_id"])

    def test_empty_message_is_refused_before_anything_is_spent(self):
        fake = FakeChatClient()

        with self.assertRaises(AgentChatMessageError):
            AgentChatUseCase.send(self.user, self.session, "   ", client=fake)

        self.assertEqual(fake.calls, [])

    @override_settings(AGENT_CHAT_MAX_MESSAGE=10, CACHES=LOCAL_CACHE)
    def test_long_message_is_truncated_not_rejected(self):
        fake = FakeChatClient()

        AgentChatUseCase.send(self.user, self.session, "a" * 500, client=fake)

        self.assertEqual(fake.calls[0]["message"], "a" * 10)

    @override_settings(AGENT_CHAT_RATE_PER_MINUTE=2, CACHES=LOCAL_CACHE)
    def test_rate_limit_stops_the_burst_without_calling_n8n(self):
        fake = FakeChatClient()

        AgentChatUseCase.send(self.user, self.session, "1", client=fake)
        AgentChatUseCase.send(self.user, self.session, "2", client=fake)
        with self.assertRaises(AgentChatRateLimitedError) as ctx:
            AgentChatUseCase.send(self.user, self.session, "3", client=fake)

        # Nothing was sent for the refused message: an over-quota user costs nothing.
        self.assertEqual(len(fake.calls), 2)
        self.assertGreater(ctx.exception.retry_after, 0)

    @override_settings(AGENT_CHAT_RATE_PER_MINUTE=100, AGENT_CHAT_RATE_PER_DAY=1, CACHES=LOCAL_CACHE)
    def test_daily_limit_catches_a_slow_drip(self):
        fake = FakeChatClient()

        AgentChatUseCase.send(self.user, self.session, "1", client=fake)
        with self.assertRaises(AgentChatRateLimitedError):
            AgentChatUseCase.send(self.user, self.session, "2", client=fake)

    @override_settings(AGENT_CHAT_RATE_PER_MINUTE=1, CACHES=LOCAL_CACHE)
    def test_limits_are_counted_per_user(self):
        other = get_user_model().objects.create_user(username="__ut_chat_other__", password="x")
        fake = FakeChatClient()

        AgentChatUseCase.send(self.user, self.session, "mine", client=fake)
        AgentChatUseCase.send(other, self.session, "theirs", client=fake)

        self.assertEqual(len(fake.calls), 2)


@override_settings(CACHES=LOCAL_CACHE, N8N_AGENT_WEBHOOK_URL="http://n8n:5678/webhook/cooking-agent")
class N8nAgentChatClientTests(TestCase):
    """Transport: what counts as an answer and what counts as a failure."""

    POST_TARGET = "recipe_manager.infrastructure.agent.chat_client.requests.post"

    def _response(self, status=200, payload=None, text=""):
        class FakeResponse:
            status_code = status

            def json(self):
                if payload is None:
                    raise ValueError("no json")
                return payload

        FakeResponse.text = text
        return FakeResponse()

    def test_returns_the_reply_text(self):
        with patch(self.POST_TARGET, return_value=self._response(payload={"reply": "  Borscht.  "})):
            reply = N8nAgentChatClient().ask("hi", "ctx", "sid")

        self.assertEqual(reply, "Borscht.")

    def test_sends_the_agreed_payload(self):
        # `settings` is always present, even empty: an n8n expression reading
        # $json.settings.use_tastes must not fail on a missing key.
        with patch(self.POST_TARGET, return_value=self._response(payload={"reply": "ok"})) as post:
            N8nAgentChatClient().ask("hi", "ctx", "sid")

        self.assertEqual(
            post.call_args.kwargs["json"],
            {"message": "hi", "context": "ctx", "sid": "sid", "settings": {}},
        )

    @override_settings(N8N_AGENT_WEBHOOK_URL="")
    def test_missing_url_is_a_configuration_error(self):
        with self.assertRaises(AgentChatNotConfiguredError):
            N8nAgentChatClient().ask("hi", "ctx", "sid")

    def test_timeout_becomes_unavailable(self):
        with patch(self.POST_TARGET, side_effect=requests.Timeout("too slow")):
            with self.assertRaises(AgentChatUnavailableError):
                N8nAgentChatClient().ask("hi", "ctx", "sid")

    def test_non_200_becomes_unavailable(self):
        with patch(self.POST_TARGET, return_value=self._response(status=500, text="boom")):
            with self.assertRaises(AgentChatUnavailableError):
                N8nAgentChatClient().ask("hi", "ctx", "sid")

    def test_missing_reply_key_is_a_response_error(self):
        with patch(self.POST_TARGET, return_value=self._response(payload={"output": "wrong key"})):
            with self.assertRaises(AgentChatResponseError):
                N8nAgentChatClient().ask("hi", "ctx", "sid")

    def test_empty_reply_is_a_response_error(self):
        # Usually means the agent hit its iteration ceiling; a blank bubble
        # would look like the assistant ignoring the user.
        with patch(self.POST_TARGET, return_value=self._response(payload={"reply": "   "})):
            with self.assertRaises(AgentChatResponseError):
                N8nAgentChatClient().ask("hi", "ctx", "sid")


@override_settings(CACHES=LOCAL_CACHE)
class AgentChatViewTests(TestCase):
    """The endpoint the future chat panel will call."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="__ut_chat_view__", password="secret123")

    def setUp(self):
        cache.clear()
        self.url = reverse("agent_chat")

    def _login(self):
        self.client.login(username="__ut_chat_view__", password="secret123")

    def test_guest_gets_json_401_not_a_redirect(self):
        response = self.client.post(self.url, {"message": "hi"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["error"], "auth_required")

    def test_reply_is_returned_to_the_caller(self):
        self._login()
        with patch(
            "recipe_manager.application.use_cases.agent_chat.N8nAgentChatClient",
            return_value=FakeChatClient("Pilaf, 40 minutes."),
        ):
            response = self.client.post(self.url, {"message": "что приготовить?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["reply"], "Pilaf, 40 minutes.")

    def test_empty_message_is_a_400(self):
        self._login()
        response = self.client.post(self.url, {"message": ""})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"], "empty_message")

    @override_settings(AGENT_CHAT_RATE_PER_MINUTE=1, CACHES=LOCAL_CACHE)
    def test_rate_limit_answers_429_with_retry_after(self):
        self._login()
        with patch(
            "recipe_manager.application.use_cases.agent_chat.N8nAgentChatClient",
            return_value=FakeChatClient(),
        ):
            self.client.post(self.url, {"message": "1"})
            response = self.client.post(self.url, {"message": "2"})

        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
        self.assertGreater(json.loads(response.content)["retry_after"], 0)

    def test_backend_failure_does_not_leak_the_cause(self):
        self._login()
        with patch(
            "recipe_manager.application.use_cases.agent_chat.N8nAgentChatClient",
            return_value=FakeChatClient(error=AgentChatUnavailableError("connect to n8n:5678 refused")),
        ):
            with self.assertLogs("recipe_manager.views.agent_chat_views", level="WARNING"):
                response = self.client.post(self.url, {"message": "hi"})

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("5678", json.loads(response.content)["detail"])

    def test_reset_hands_back_a_new_conversation_id(self):
        self._login()
        with patch(
            "recipe_manager.application.use_cases.agent_chat.N8nAgentChatClient",
            return_value=FakeChatClient(),
        ):
            first = json.loads(self.client.post(self.url, {"message": "hi"}).content)["chat_id"]

        reset = json.loads(self.client.post(reverse("agent_chat_reset")).content)

        self.assertEqual(reset["status"], "success")
        self.assertNotEqual(reset["chat_id"], first)
