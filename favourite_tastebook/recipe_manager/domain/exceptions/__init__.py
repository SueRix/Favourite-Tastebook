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

from .generated_recipe import (
    GeneratedRecipeException,
    GeneratedRecipeAlreadySavedError,
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

    # Generated recipes
    "GeneratedRecipeException",
    "GeneratedRecipeAlreadySavedError",
    "UnknownIngredientsError",
    "TabooIngredientError",
]
