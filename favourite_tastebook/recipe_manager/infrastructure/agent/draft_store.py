from django.conf import settings
from django.core.cache import cache

KEY_PREFIX = "agent-draft"


class AgentDraftStore:
    """
    What: Holds the recipe the agent proposed during one turn, keyed by the
          conversation id.
    Where: Written by the `propose_recipe` tool as it answers n8n; read by the
           chat use case right after the agent's reply comes back.
    Why: The draft and the reply travel to the browser by different routes. The
         reply is the webhook's return value; the proposal is a side effect of a
         tool call that happened somewhere in the middle of the agent's thinking,
         on a separate HTTP request. This is the join between them — the agent
         leaves the structured recipe here under the conversation id, and the
         view picks it up when the prose arrives.

    Cache rather than a table on purpose: a draft is worthless once the person
    has either kept it or asked for something else, and giving it a row would
    mean owning its lifecycle for no gain.
    """

    @classmethod
    def _key(cls, sid: str) -> str:
        return f"{KEY_PREFIX}:{sid}"

    @classmethod
    def put(cls, sid: str, draft: dict) -> None:
        if not sid:
            return
        cache.set(cls._key(sid), draft, settings.AGENT_DRAFT_TTL)

    @classmethod
    def take(cls, sid: str) -> dict | None:
        """
        Reads the draft and removes it: it belongs to the turn that produced it.
        Leaving it in place would re-deliver a stale recipe on the next message
        and overwrite whatever the person had already edited on screen.
        """
        if not sid:
            return None

        key = cls._key(sid)
        draft = cache.get(key)
        if draft is not None:
            cache.delete(key)
        return draft

    @classmethod
    def clear(cls, sid: str) -> None:
        """Called before a message is sent, so a reply can only carry its own draft."""
        if sid:
            cache.delete(cls._key(sid))
