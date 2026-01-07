from .base import RecipeManagerException


class SelectorException(RecipeManagerException):
    """Base exception for data selection errors."""
    pass


class EmptyQueryValueError(SelectorException):
    """
    Raised when a query parameter key is present, but one of its values is empty.
    Example: ?ingredient=&ingredient=5
    """
    pass
