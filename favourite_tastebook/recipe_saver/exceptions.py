class SavedRecipeException(Exception):
    message = "An error occurred while processing saved recipes."

class RecipeAlreadySavedError(SavedRecipeException):
    message = "This recipe is already in your saved list."

class RecipeNotFoundError(SavedRecipeException):
    message = "The specified recipe does not exist."