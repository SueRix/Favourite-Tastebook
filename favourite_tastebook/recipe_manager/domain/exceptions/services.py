from .base import RecipeManagerException

class ServiceException(RecipeManagerException):
    """Base exception for service layer operations."""
    pass

class InvalidWeightConfigurationError(ServiceException):
    """Raised when the provided weight configuration is invalid or incomplete."""
    pass

class EmptyIngredientsError(ServiceException):
    """Raised when an operation requires ingredients but none were provided."""
    pass