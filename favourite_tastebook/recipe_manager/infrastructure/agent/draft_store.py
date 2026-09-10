from django.conf import settings
from django.core.cache import cache

KEY_PREFIX = "agent-draft"
SAVED_KEY_PREFIX = "agent-saved"


class AgentDraftStore:
    """
    What: Holds what the agent did to a recipe during one turn, keyed by the
          conversation id — the dish it proposed, and the dish it stored.
    Where: Written by the `propose_recipe` and `save_generated_recipe` tools as
           they answer n8n; read by the chat use case right after the agent's
           reply comes back.
    Why: The recipe and the reply travel to the browser by different routes. The
         reply is the webhook's return value; the recipe is a side effect of a
         tool call that happened somewhere in the middle of the agent's thinking,
         on a separate HTTP request. This is the join between them — the agent
         leaves the structured recipe here under the conversation id, and the
         view picks it up when the prose arrives.

    Two slots rather than one, because the browser has to react differently to
    each. A proposal is an offer: the studio prints it with the buttons that
    decide its fate. A save has already happened: nothing is left to decide, and
    the only correct response is to show the creations list catching up with it.

    Cache rather than a table on purpose: both are worthless once the person has
    seen them, and giving them rows would mean owning their lifecycle for no gain.
    """

    @classmethod
    def _key(cls, sid: str) -> str:
        return f"{KEY_PREFIX}:{sid}"

    @classmethod
    def _saved_key(cls, sid: str) -> str:
        return f"{SAVED_KEY_PREFIX}:{sid}"

    @classmethod
    def _take(cls, key: str) -> dict | None:
        value = cache.get(key)
        if value is not None:
            cache.delete(key)
        return value

    # ------------------------------------------------------------- proposals

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
        return cls._take(cls._key(sid))

    # ----------------------------------------------------------------- saves

    @classmethod
    def put_saved(cls, sid: str, recipe: dict) -> None:
        """
        Records a recipe the agent stored on its own, so the page can show the
        new creation without a reload. The recipe already exists in the database
        at this point; this is only how the browser hears about it.
        """
        if not sid:
            return
        cache.set(cls._saved_key(sid), recipe, settings.AGENT_DRAFT_TTL)

    @classmethod
    def take_saved(cls, sid: str) -> dict | None:
        """One-shot for the same reason `take` is: it announces one event, once."""
        if not sid:
            return None
        return cls._take(cls._saved_key(sid))

    # ----------------------------------------------------------------- reset

    @classmethod
    def clear(cls, sid: str) -> None:
        """Called before a message is sent, so a reply can only carry its own turn."""
        if sid:
            cache.delete_many([cls._key(sid), cls._saved_key(sid)])
