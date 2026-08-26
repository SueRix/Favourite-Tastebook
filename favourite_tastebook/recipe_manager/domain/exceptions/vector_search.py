from .base import RecipeManagerException


class VectorSearchException(RecipeManagerException):
    """Base exception for the vector-similarity selection path."""
    pass


class VectorBackendUnavailableError(VectorSearchException):
    """Raised when the n8n / Pinecone webhook cannot be reached or times out."""
    message = "Vector search backend is currently unavailable."


class VectorBackendResponseError(VectorSearchException):
    """Raised when the webhook responds with an unexpected status or malformed payload."""
    message = "Vector search backend returned an invalid response."