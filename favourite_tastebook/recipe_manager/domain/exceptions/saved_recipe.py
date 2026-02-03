class SavedRecipeException(Exception):
    message = "An error occurred while processing saved recipes."

    def __init__(self, message=None):
        super().__init__(message or self.message)

class RecipeAlreadySavedError(SavedRecipeException):
    message = "This recipe is already in your saved list."

class RecipeNotFoundError(SavedRecipeException):
    message = "The specified recipe does not exist."