from uuid import uuid4


class AgentChatSession:
    """
    What: Owns the id that identifies ONE conversation with the cooking agent.
    Where: Read by the chat view on every message; passed to n8n as `sid` and
           signed into the agent context alongside the user id.
    Why: n8n keys the agent's memory by this value, so it decides two things at
         once — who shares a conversation history, and where a conversation ends.
         Django's own session_key would be the obvious candidate and is the wrong
         one: it is absent until something is written to the session (every user
         would then land in a single shared history under the string "None"), and
         starting a fresh conversation would mean cycling the key the login
         depends on. A dedicated id keeps "new chat" a one-line operation that
         touches nothing else.
    """

    #: Key under which the id lives in the Django session.
    SESSION_KEY = "agent_chat_id"

    @classmethod
    def current(cls, session) -> str:
        """The id of the running conversation, creating one on first use."""
        chat_id = session.get(cls.SESSION_KEY)
        if not chat_id:
            chat_id = cls._new(session)
        return chat_id

    @classmethod
    def reset(cls, session) -> str:
        """
        Starts a fresh conversation. The old history is not deleted — it simply
        stops being addressed, and n8n's memory window lets it fall out on its
        own. Nothing else in the session is touched, so the user stays logged in.
        """
        return cls._new(session)

    @classmethod
    def _new(cls, session) -> str:
        # uuid4 hex: 32 chars, comfortably inside both the signed context and
        # GeneratedRecipe.session_id, and carrying nothing about the user.
        chat_id = uuid4().hex
        session[cls.SESSION_KEY] = chat_id
        return chat_id
