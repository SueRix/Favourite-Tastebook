from recipe_manager.domain.parsers.recipe_steps import RecipeStepsParser


class FeaturedRecipePresenter:
    """
    Presentation adapter: prepares ORM objects for templates.
    (Yes, it mutates object with .steps intentionally for template convenience.)
    """

    @classmethod
    def select(cls, recipes, recipe_id=None):
        if not recipes.exists():
            return None, recipes.none()

        featured = None
        if recipe_id:
            featured = recipes.filter(id=recipe_id).first()

        if featured is None:
            featured = recipes.first()

        featured.steps = RecipeStepsParser.parse(featured.description)
        more = recipes.exclude(id=featured.id)
        return featured, more
