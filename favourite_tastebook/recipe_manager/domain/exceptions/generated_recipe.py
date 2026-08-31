from .base import RecipeManagerException


class GeneratedRecipeException(RecipeManagerException):
    """Base exception for recipes the agent composed rather than found."""
    message = "The generated recipe could not be saved."


class GeneratedRecipeAlreadySavedError(GeneratedRecipeException):
    """Raised when this user already keeps a generated recipe under the same title."""
    message = "This recipe is already in your saved list."


class UnknownIngredientsError(GeneratedRecipeException):
    """
    Raised when the agent used an ingredient that is not in the catalogue.

    Carries the offending names: the agent has to READ them in order to swap in
    something we actually know, so they are part of the contract, not just log text.
    """
    message = "Some ingredients are not in the catalogue."

    def __init__(self, names, message: str | None = None):
        self.names = list(names)
        super().__init__(
            message or f"Not in the ingredient catalogue: {', '.join(self.names)}."
        )


class TabooIngredientError(GeneratedRecipeException):
    """
    Raised when a generated recipe contains an ingredient the user marked as
    never_use. The system prompt already forbids it, but a prompt is advice; this
    is the check that actually holds, and it runs before anything is written.
    """
    message = "The recipe contains an ingredient this user never wants to use."

    def __init__(self, names, message: str | None = None):
        self.names = list(names)
        super().__init__(
            message or f"The user never uses: {', '.join(self.names)}."
        )
