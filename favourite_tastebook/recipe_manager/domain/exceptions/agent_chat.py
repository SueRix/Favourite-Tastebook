from .base import RecipeManagerException


class AgentChatException(RecipeManagerException):
    """Base exception for the browser-facing chat with the cooking agent."""
    message = "The cooking assistant is unavailable right now."


class AgentChatNotConfiguredError(AgentChatException):
    """Raised when the agent webhook URL is absent, so there is nothing to talk to."""
    message = "The cooking assistant is not configured."


class AgentChatMessageError(AgentChatException):
    """Raised when the user sent nothing to say."""
    message = "Write a message first."


class AgentChatRateLimitedError(AgentChatException):
    """
    Raised when this user has spent their allowance.

    Carries `retry_after` in seconds: a chat that says "come back later" without
    saying how much later reads as a breakage rather than a limit.
    """
    message = "Too many messages. Give the assistant a moment."

    def __init__(self, retry_after: int, message: str | None = None):
        self.retry_after = retry_after
        super().__init__(message)


class AgentChatUnavailableError(AgentChatException):
    """Raised when the n8n webhook could not be reached or timed out."""
    message = "The cooking assistant did not answer in time."


class AgentChatResponseError(AgentChatException):
    """Raised when n8n answered with something that is not a chat reply."""
    message = "The cooking assistant returned an unexpected answer."
