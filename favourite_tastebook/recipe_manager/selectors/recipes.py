from recipe_manager.models import Recipe

class RecipeSelector:
    @classmethod
    def get_base_queryset(cls):
        return Recipe.objects.select_related("cuisine").all()