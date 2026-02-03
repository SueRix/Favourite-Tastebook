from recipe_manager.domain.parsers import RecipeStepsParser

class SavedRecipePresenter:
    def __init__(self, saved_recipes_queryset):
        self.queryset = saved_recipes_queryset

    def data(self):
        return [self._transform(item) for item in self.queryset]

    @staticmethod
    def _transform(saved_item):
        recipe = saved_item.recipe
        steps = RecipeStepsParser.parse(recipe.description)

        return {
            "id": recipe.id,
            "title": recipe.title,
            "cook_time": recipe.cook_time,
            "image": recipe.image_url.url if recipe.image_url else None,
            "instructions": steps,
            "cuisine": recipe.cuisine.name if recipe.cuisine else None,
            "saved_at": saved_item.created_at.strftime("%d.%m.%Y")
        }