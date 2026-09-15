import requests
from django.conf import settings

from recipe_manager.domain.exceptions import (
    AgentChatNotConfiguredError,
    AgentChatResponseError,
    AgentChatUnavailableError,
)


class N8nAgentChatClient:
    """
    What: Thin HTTP client for the n8n workflow that runs the cooking agent.
    Where: Used by AgentChatUseCase; the only place in Django that knows the
           webhook exists.
    Why: Same division as N8nPineconeClient — URL, auth, timeout, payload shape
         and error translation live here so the use case stays pure logic. The
         two clients are deliberately separate rather than one generic helper:
         they answer on different timescales (a search in a second, an agent in
         twenty) and fail for different reasons, and merging them would mean one
         timeout serving both badly.

    Contract with the workflow:
        Request  (POST, JSON):  {"message": str, "context": str, "sid": str,
                                 "settings": {...}}
        Response (JSON):        {"reply": str}

    The `settings` key carries the switches the user set in the studio, so the
    workflow can build the system prompt around them. It is called `preferences`
    on this side, where `settings` already means Django's. It is advice to the
    model, not a control: every one of those switches is also enforced by the
    tool endpoints, which is what makes it hold when the model is talked out
    of it.
    """

    def __init__(self, webhook_url: str = None, auth_token: str = None, timeout: float = None):
        self.webhook_url = webhook_url if webhook_url is not None else settings.N8N_AGENT_WEBHOOK_URL
        self.auth_token = auth_token if auth_token is not None else settings.N8N_WEBHOOK_AUTH_TOKEN
        self.timeout = timeout or settings.AGENT_CHAT_TIMEOUT

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def ask(self, message: str, context: str, sid: str, preferences: dict = None) -> str:
        """Sends one turn of the conversation and returns the agent's reply text."""
        if not self.webhook_url:
            raise AgentChatNotConfiguredError("N8N_AGENT_WEBHOOK_URL is not configured.")

        # Always present, even when empty: a workflow expression reading
        # {{ $json.settings.use_tastes }} must not fail on a missing key for the
        # users who have never opened the settings panel.
        payload = {"message": message, "context": context, "sid": sid, "settings": preferences or {}}

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise AgentChatUnavailableError(f"Agent webhook request failed: {exc}") from exc

        if response.status_code != 200:
            raise AgentChatUnavailableError(
                f"Agent webhook returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            reply = response.json()["reply"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AgentChatResponseError(f"Malformed agent webhook payload: {exc}") from exc

        if not isinstance(reply, str) or not reply.strip():
            # An empty reply usually means the agent hit its iteration ceiling.
            # Surfacing it as a failure beats showing the user a blank bubble.
            raise AgentChatResponseError("Agent webhook returned an empty reply.")

        return reply.strip()
