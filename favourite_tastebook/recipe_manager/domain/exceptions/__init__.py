from .base import RecipeManagerException

from .services import (
    ServiceException,
    InvalidWeightConfigurationError,
    EmptyIngredientsError,
)

from .selectors import SelectorException, EmptyQueryValueError

from .vector_search import (
    VectorSearchException,
    VectorBackendUnavailableError,
    VectorBackendResponseError,
)

from .agent_chat import (
    AgentChatException,
    AgentChatNotConfiguredError,
    AgentChatMessageError,
    AgentChatRateLimitedError,
    AgentChatUnavailableError,
    AgentChatResponseError,
)

from .generated_recipe import (
    GeneratedRecipeException,
    GeneratedRecipeAlreadySavedError,
    GeneratedRecipeNotFoundError,
    UnknownIngredientsError,
    TabooIngredientError,
)

from .agent import (
    AgentToolException,
    AgentNotConfiguredError,
    AgentAuthError,
    AgentContextError,
    AgentPayloadError,
)

__all__ = [
    # Base
    "RecipeManagerException",

    # Services
    "ServiceException",
    "InvalidWeightConfigurationError",
    "EmptyIngredientsError",

    # Selectors
    "SelectorException",
    "EmptyQueryValueError",

    # Vector search
    "VectorSearchException",
    "VectorBackendUnavailableError",
    "VectorBackendResponseError",

    # Agent tool API
    "AgentToolException",
    "AgentNotConfiguredError",
    "AgentAuthError",
    "AgentContextError",
    "AgentPayloadError",

    # Agent chat
    "AgentChatException",
    "AgentChatNotConfiguredError",
    "AgentChatMessageError",
    "AgentChatRateLimitedError",
    "AgentChatUnavailableError",
    "AgentChatResponseError",

    # Generated recipes
    "GeneratedRecipeException",
    "GeneratedRecipeAlreadySavedError",
    "GeneratedRecipeNotFoundError",
    "UnknownIngredientsError",
    "TabooIngredientError",
]
