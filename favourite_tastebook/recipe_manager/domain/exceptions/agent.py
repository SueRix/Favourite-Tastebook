from .base import RecipeManagerException


class AgentToolException(RecipeManagerException):
    """Base exception for the n8n agent tool API."""
    pass


class AgentNotConfiguredError(AgentToolException):
    """Raised when the shared service token is absent, so the API cannot authenticate anyone."""
    message = "Agent tool API is not configured."


class AgentAuthError(AgentToolException):
    """Raised when the caller did not present the shared service token."""
    message = "Agent request could not be authenticated."


class AgentContextError(AgentToolException):
    """Raised when the signed user context is missing, tampered with or expired."""
    message = "Agent context is missing, invalid or expired."


class AgentPayloadError(AgentToolException):
    """Raised when the JSON body does not satisfy a tool's input contract."""
    message = "Agent request payload is malformed."
