import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from recipe_manager.application.use_cases.agent_chat import AgentChatUseCase
from recipe_manager.application.use_cases.agent_settings import AgentSettingsUseCase
from recipe_manager.domain.exceptions import (
    AgentChatMessageError,
    AgentChatNotConfiguredError,
    AgentChatRateLimitedError,
    AgentChatResponseError,
    AgentChatUnavailableError,
    AgentPayloadError,
)

logger = logging.getLogger(__name__)


class JsonLoginRequiredMixin(LoginRequiredMixin):
    """
    Answers an unauthenticated call with 401 JSON instead of a redirect.

    The chat is called by script, not by following links: a 302 to the login page
    would arrive as a chunk of HTML in place of a reply, and the panel would
    render the login form as if the assistant had said it.
    """

    def handle_no_permission(self):
        return JsonResponse({"error": "auth_required", "detail": "Sign in to use the assistant."}, status=401)


class AgentChatView(JsonLoginRequiredMixin, View):
    """
    POST /home/chat/ — send one message, get the agent's reply.

    Body: form field or JSON key `message`.
    Answers {"reply": str, "chat_id": str}, or {"error", "detail"} with a status.
    """

    def post(self, request, *args, **kwargs):
        message = request.POST.get("message", "")

        try:
            result = AgentChatUseCase.send(request.user, request.session, message)
        except AgentChatMessageError as exc:
            return JsonResponse({"error": "empty_message", "detail": exc.message}, status=400)
        except AgentChatRateLimitedError as exc:
            # Retry-After is the header a browser and a human both understand.
            response = JsonResponse(
                {"error": "rate_limited", "detail": exc.message, "retry_after": exc.retry_after},
                status=429,
            )
            response["Retry-After"] = str(exc.retry_after)
            return response
        except AgentChatNotConfiguredError as exc:
            logger.error("Agent chat refused a message: %s", exc)
            return JsonResponse({"error": "not_configured", "detail": exc.message}, status=503)
        except (AgentChatUnavailableError, AgentChatResponseError) as exc:
            # Log the cause, show the class-level sentence: the user can do
            # nothing with a timeout trace, and it would leak our topology.
            logger.warning("Agent chat failed: %s", exc)
            return JsonResponse({"error": "unavailable", "detail": type(exc).message}, status=503)

        return JsonResponse(result)


class AgentChatResetView(JsonLoginRequiredMixin, View):
    """
    POST /home/chat/reset/ — start a new conversation.

    Nothing is deleted; the next message simply travels under a new id, so the
    agent begins with a clean history.
    """

    def post(self, request, *args, **kwargs):
        chat_id = AgentChatUseCase.reset(request.session)
        return JsonResponse({"status": "success", "chat_id": chat_id})


class AgentSettingsView(JsonLoginRequiredMixin, View):
    """
    GET  /home/chat/settings/ — how the assistant is currently set up.
    POST /home/chat/settings/ — change one or more of those switches.

    The POST body is a JSON object holding only the switches that moved, so the
    panel never has to send back values it did not touch. Answers the full,
    stored settings either way, which is what the page renders from: a switch
    shows what the server holds, not what the click assumed.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "success", "settings": AgentSettingsUseCase.read(request.user)})

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"error": "bad_request", "detail": "Malformed settings."}, status=400)

        try:
            settings_ = AgentSettingsUseCase.update(request.user, payload)
        except AgentPayloadError as exc:
            return JsonResponse({"error": "invalid", "detail": str(exc)}, status=400)

        return JsonResponse({"status": "success", "settings": settings_})
