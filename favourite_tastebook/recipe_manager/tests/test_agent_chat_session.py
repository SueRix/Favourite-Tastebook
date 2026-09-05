from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase

from recipe_manager.infrastructure.agent import AgentChatSession, AgentContextToken


class AgentChatSessionTests(TestCase):
    """
    Covers the id that tells n8n which conversation a message belongs to.

    It is deliberately not Django's session_key: these tests pin the two
    properties that choice buys — an id that exists before anything else is
    written to the session, and a reset that leaves the login alone.
    """

    def setUp(self):
        self.session = SessionStore()

    def test_created_on_first_use(self):
        chat_id = AgentChatSession.current(self.session)

        self.assertTrue(chat_id)
        self.assertEqual(self.session[AgentChatSession.SESSION_KEY], chat_id)

    def test_stable_across_calls(self):
        first = AgentChatSession.current(self.session)
        self.assertEqual(AgentChatSession.current(self.session), first)

    def test_available_before_the_session_is_saved(self):
        # session_key is None until the store is written; this id is not.
        self.assertIsNone(self.session.session_key)
        self.assertTrue(AgentChatSession.current(self.session))

    def test_survives_a_save_and_reload(self):
        chat_id = AgentChatSession.current(self.session)
        self.session.save()

        reloaded = SessionStore(session_key=self.session.session_key)
        self.assertEqual(AgentChatSession.current(reloaded), chat_id)

    def test_reset_starts_a_new_conversation(self):
        first = AgentChatSession.current(self.session)
        second = AgentChatSession.reset(self.session)

        self.assertNotEqual(second, first)
        self.assertEqual(AgentChatSession.current(self.session), second)

    def test_reset_touches_nothing_else(self):
        self.session["_auth_user_id"] = "42"
        AgentChatSession.current(self.session)
        AgentChatSession.reset(self.session)

        self.assertEqual(self.session["_auth_user_id"], "42")

    def test_two_sessions_do_not_share_a_conversation(self):
        other = SessionStore()

        self.assertNotEqual(
            AgentChatSession.current(self.session),
            AgentChatSession.current(other),
        )

    def test_id_fits_the_signed_context_round_trip(self):
        chat_id = AgentChatSession.current(self.session)
        parsed = AgentContextToken.parse(AgentContextToken.issue(7, chat_id))

        self.assertEqual(parsed, {"uid": 7, "sid": chat_id})
