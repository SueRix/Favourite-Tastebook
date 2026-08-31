import json
import logging
from functools import wraps

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils.crypto import constant_time_compare

from recipe_manager.domain.exceptions import (
    AgentAuthError,
    AgentContextError,
    AgentNotConfiguredError,
    AgentPayloadError,
    VectorSearchException,
)
from recipe_manager.infrastructure.agent.context_token import AgentContextToken

logger = logging.getLogger(__name__)

# Shared secret proving the caller is our own n8n instance.
SERVICE_TOKEN_HEADER = "X-Agent-Token"
# Signed blob identifying the human behind the conversation. n8n copies it from
# the webhook payload into this header with an expression, so it never becomes a
# tool argument the model could invent.
CONTEXT_HEADER = "X-Agent-Context"

MAX_BODY_BYTES = 8 * 1024


def _authenticate_service(request) -> None:
    expected = settings.AGENT_SERVICE_TOKEN
    if not expected:
        # Fail closed. An unset secret must not silently mean "no auth needed",
        # or a misconfigured deploy would expose the whole tool surface.
        raise AgentNotConfiguredError("AGENT_SERVICE_TOKEN is not set.")

    provided = request.headers.get(SERVICE_TOKEN_HEADER, "")
    if not constant_time_compare(provided, expected):
        raise AgentAuthError()


def _resolve_user(uid):
    """
    None means an anonymous chat, which is a supported state — the tools degrade
    to public data. A uid that no longer resolves (deleted account, stale token)
    is treated the same way rather than as an error.
    """
    if uid is None:
        return None

    user = get_user_model().objects.filter(pk=uid).first()
    if user is None:
        logger.warning("Agent context references unknown user id %s", uid)
    return user


def _parse_body(request) -> dict:
    if not request.body:
        # A tool with no arguments (user_tastes) legitimately posts nothing.
        return {}

    if len(request.body) > MAX_BODY_BYTES:
        raise AgentPayloadError("Agent request body is too large.")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise AgentPayloadError(f"Body is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise AgentPayloadError("Body must be a JSON object.")
    return data


def agent_tool(func):
    """
    What: Turns a plain view method into an n8n tool endpoint — authenticates the
          calling service, resolves the acting user from the signed context,
          parses the JSON body and normalises every failure into JSON.
    Where: Applied to the post() of every view in views/agent_tool_views.py.
    Why: Two different kinds of failure meet here and must not be conflated.
         Transport problems (wrong secret, forged context, unparsable body) are
         answered with 4xx/5xx: the agent has no business seeing them and the
         model should never be handed a hint about our auth scheme. Domain
         outcomes (recipe not found, search backend down) come back as HTTP 200
         with "ok": false, because the agent has to read them in order to explain
         itself to the user — an HTTP error would surface as a broken tool call.

    Provides on the request: `agent_user`, `agent_session_id`, `agent_payload`.
    """

    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        try:
            _authenticate_service(request)
            context = AgentContextToken.parse(request.headers.get(CONTEXT_HEADER))
        except AgentNotConfiguredError as exc:
            logger.error("Agent tool API refused a call: %s", exc)
            return JsonResponse({"detail": exc.message}, status=503)
        except (AgentAuthError, AgentContextError) as exc:
            # Log the specifics, return the generic class-level message: the
            # caller learns nothing about which half of the handshake failed.
            logger.warning("Agent tool auth rejected: %s", exc)
            return JsonResponse({"detail": type(exc).message}, status=401)

        request.agent_user = _resolve_user(context["uid"])
        request.agent_session_id = context["sid"]

        try:
            request.agent_payload = _parse_body(request)
            return func(self, request, *args, **kwargs)
        except AgentPayloadError as exc:
            # The model can fix this one by calling again with better arguments,
            # so the detail is deliberately specific.
            logger.info("Agent tool payload rejected: %s", exc)
            return JsonResponse({"ok": False, "error": "bad_request", "detail": str(exc)}, status=400)
        except VectorSearchException as exc:
            logger.warning("Agent tool vector backend failure: %s", exc)
            return JsonResponse(
                {"ok": False, "error": "search_unavailable", "detail": type(exc).message},
                status=200,
            )

    return wrapper
