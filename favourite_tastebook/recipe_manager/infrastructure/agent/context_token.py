from django.conf import settings
from django.core import signing

from recipe_manager.domain.exceptions import AgentContextError

# Namespaces the signature: a token minted for the agent cannot be replayed
# against any other django.core.signing consumer in the project.
CONTEXT_SALT = "recipe_manager.agent.context"


class AgentContextToken:
    """
    What: Mints and verifies the opaque token that carries WHO is chatting
          (user id) and WHICH conversation it is (session id) across the
          Django -> n8n -> Django round trip.
    Where: Issued by the chat view before calling the n8n agent webhook; parsed
           back by the @agent_tool decorator on every tool endpoint.
    Why: The acting user must never be a tool argument. If the LLM could pass a
         user_id, a prompt-injected recipe or a curious user could make the agent
         read or modify somebody else's profile. n8n forwards this blob verbatim
         in a header it fills from the webhook payload, so the model never sees
         it and cannot forge it: the signature is keyed on SECRET_KEY, and the
         max-age bounds how long a leaked token stays useful.
    """

    @staticmethod
    def issue(user_id, session_id) -> str:
        """user_id is None for guests: an anonymous chat is still a valid session."""
        return signing.dumps(
            {"uid": int(user_id) if user_id is not None else None, "sid": str(session_id)},
            salt=CONTEXT_SALT,
        )

    @staticmethod
    def parse(raw: str, max_age: int = None) -> dict:
        """
        Returns {"uid": int | None, "sid": str}.
        Raises AgentContextError for anything that is not a token this project
        signed itself and that is still inside its lifetime.
        """
        if not raw:
            raise AgentContextError("Agent context header is absent.")

        try:
            data = signing.loads(
                raw,
                salt=CONTEXT_SALT,
                max_age=max_age if max_age is not None else settings.AGENT_CONTEXT_MAX_AGE,
            )
        except signing.SignatureExpired as exc:
            raise AgentContextError(f"Agent context expired: {exc}") from exc
        except signing.BadSignature as exc:
            raise AgentContextError(f"Agent context signature is invalid: {exc}") from exc

        # A valid signature only proves WE minted it, not that the shape is right
        # (an older token format would sail straight through otherwise).
        if not isinstance(data, dict) or "sid" not in data:
            raise AgentContextError("Agent context payload has an unexpected shape.")

        uid = data.get("uid")
        if uid is not None and not isinstance(uid, int):
            raise AgentContextError("Agent context carries a non-integer user id.")

        return {"uid": uid, "sid": str(data["sid"])}
