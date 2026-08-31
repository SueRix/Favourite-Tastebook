from django.conf import settings

from recipe_manager.domain.exceptions import AgentChatMessageError
from recipe_manager.infrastructure.agent import (
    AgentChatRateLimiter,
    AgentChatSession,
    AgentContextToken,
    AgentDraftStore,
    N8nAgentChatClient,
)


class AgentChatUseCase:
    """
    What: One turn of the conversation between a signed-in user and the agent.
    Where: Called by the chat view; the view itself only maps failures to codes.
    Why: Everything that must happen on OUR side of the webhook lives here and
         in one order — check the allowance, clean the message, mint the signed
         context, then send. The order matters: the rate check comes first so a
         user over their limit costs us nothing at all, and the context is minted
         last and never cached, so its one-hour lifetime is spent on the single
         request it was issued for.

    The user is never a parameter of the outgoing payload. It is sealed into the
    signed context here, which is the only reason the tool API can trust it.
    """

    @classmethod
    def send(cls, user, session, message: str, client=None) -> dict:
        """
        Returns {"reply": str, "chat_id": str, "draft": dict | None}, where the
        draft is present only when the agent proposed a recipe on this turn.
        Raises AgentChatException on failure.
        """
        text = (message or "").strip()
        if not text:
            raise AgentChatMessageError()

        # Truncate rather than reject: a long message is still a question, and a
        # cap the user cannot see would look like an arbitrary refusal.
        text = text[: settings.AGENT_CHAT_MAX_MESSAGE]

        AgentChatRateLimiter.check(user.id)

        chat_id = AgentChatSession.current(session)
        context = AgentContextToken.issue(user.id, chat_id)

        # Drop anything left from an earlier turn first, so whatever is in the
        # store afterwards can only have been proposed for THIS message.
        AgentDraftStore.clear(chat_id)

        client = client or N8nAgentChatClient()
        reply = client.ask(message=text, context=context, sid=chat_id)

        # The agent may have called propose_recipe while it was thinking; that
        # call landed on a different request and left its draft here.
        return {"reply": reply, "chat_id": chat_id, "draft": AgentDraftStore.take(chat_id)}

    @classmethod
    def reset(cls, session) -> str:
        """
        Starts a new conversation. Only the id changes: the old history stays in
        n8n, unaddressed, and falls out of its memory window on its own.
        """
        AgentDraftStore.clear(AgentChatSession.current(session))
        return AgentChatSession.reset(session)
