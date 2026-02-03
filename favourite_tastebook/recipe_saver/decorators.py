from functools import wraps

from django.http import JsonResponse

from recipe_saver.exceptions import RecipeNotFoundError, RecipeAlreadySavedError


def handle_recipe_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RecipeNotFoundError as e:
            return JsonResponse({"detail": str(e)}, status=404)
        except RecipeAlreadySavedError as e:
            return JsonResponse({"detail": str(e)}, status=409)

    return wrapper