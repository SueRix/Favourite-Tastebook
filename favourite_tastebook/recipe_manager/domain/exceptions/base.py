class RecipeManagerException(Exception):
    """Base exception for the Recipe Manager application."""
    message: str = "An internal application error occurred."

    def __init__(self, message: str | None = None, *args):
        if message:
            self.message = message
        super().__init__(self.message, *args)