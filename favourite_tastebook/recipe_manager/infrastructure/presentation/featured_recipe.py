from recipe_manager.domain.enums import Importance
from recipe_manager.domain.parsers.recipe_steps import RecipeStepsParser


class FeaturedRecipePresenter:
    """
    Presentation adapter: prepares ORM objects for templates.
    (Yes, it mutates object with .steps intentionally for template convenience.)
    """

    @classmethod
    def select(cls, recipes, recipe_id=None, selected_ids=None):
        if not recipes.exists():
            return None, recipes.none()

        featured = None
        if recipe_id:
            featured = recipes.filter(id=recipe_id).first()

        if featured is None:
            featured = recipes.first()

        selected_set = set(int(x) for x in (selected_ids or []))

        featured.steps = RecipeStepsParser.parse(featured.description)
        featured.cuisine_label = featured.cuisine.name if featured.cuisine_id else "—"

        # Prefetched: featured.ingredients -> list[RecipeIngredient] with .ingredient selected
        recipe_items = list(featured.ingredients.all())

        def build_item(ri):
            ing = ri.ingredient
            return {
                # Ingredient fields
                "id": ing.id,
                "name": ing.name,
                "category": getattr(ing, "category", None),

                # Through (RecipeIngredient) fields
                "amount": ri.amount,
                "unit": ri.unit,  # value for templates (e.g. "g")
                "importance": ri.importance,

                # UI flags
                "is_selected": ing.id in selected_set,
            }

        def build_group(title: str, importance: str):
            items = [build_item(ri) for ri in recipe_items if ri.importance == importance]
            return {
                "title": title,
                "items": items,
            }

        featured.ingredient_groups = [
            build_group("Required", Importance.REQUIRED),
            build_group("Secondary", Importance.SECONDARY),
            build_group("Optional", Importance.OPTIONAL),
        ]

        featured.ingredients_detailed = [build_item(ri) for ri in recipe_items]

        # Quick counters for the UI
        featured.matched_count = sum(1 for ri in recipe_items if ri.ingredient_id in selected_set)
        featured.missing_count = len(recipe_items) - featured.matched_count

        more = recipes.exclude(id=featured.id)
        return featured, more
