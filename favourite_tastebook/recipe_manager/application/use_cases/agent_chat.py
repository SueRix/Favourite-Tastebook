from django.conf import settings

from recipe_manager.domain.exceptions import AgentChatMessageError
from recipe_manager.infrastructure.agent import (
    AgentChatRateLimiter,
    AgentChatSession,
    AgentContextToken,
    AgentDraftStore,
    N8nAgentChatClient,
)
from recipe_manager.infrastructure.selectors import AgentPreferenceSelector


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
        Returns {"reply", "chat_id", "draft", "saved", "settings",
        "autoload_draft"}. The draft is present only when the agent proposed a
        recipe on this turn; `saved` only when it stored one itself, which the
        page needs in order to show the creation without a reload.
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

        # The same switches the tool endpoints enforce also travel to the prompt.
        # Enforcement is what actually holds — a model can be talked out of an
        # instruction — but an agent that knows the rule can say "you asked me to
        # invent dishes rather than search" instead of walking into a refusal it
        # has to improvise an explanation for.
        preferences = AgentPreferenceSelector.for_user(user)

        client = client or N8nAgentChatClient()
        reply = client.ask(message=text, context=context, sid=chat_id, preferences=preferences)

        # The agent may have called propose_recipe or save_generated_recipe while
        # it was thinking; those calls landed on different requests and left what
        # they produced here.
        draft = AgentDraftStore.take(chat_id)
        saved = AgentDraftStore.take_saved(chat_id)

        return {
            "reply": reply,
            "chat_id": chat_id,
            "draft": draft,
            "saved": saved,
            "settings": preferences,
            # Whether the page may put this turn's recipe straight into the
            # editor. It covers BOTH ways one can arrive: a proposal the person
            # has yet to keep, and a dish the assistant stored itself. The
            # second is the one that actually happens most of the time, and
            # leaving it out was why the switch looked dead.
            #
            # Computed here rather than read from the browser's copy of the
            # settings, so flipping the switch in one tab cannot leave another
            # tab acting on a value that is no longer stored.
            "autoload_draft": bool(draft or saved) and preferences["autosave_drafts"],
        }

    @classmethod
    def reset(cls, session) -> str:
        """
        Starts a new conversation. Only the id changes: the old history stays in
        n8n, unaddressed, and falls out of its memory window on its own.
        """
        AgentDraftStore.clear(AgentChatSession.current(session))
        return AgentChatSession.reset(session)
