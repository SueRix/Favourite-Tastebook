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

        recipe_items = list(featured.ingredients.all())

        def build_group(title: str, importance: str):
            items = []
            for ri in recipe_items:
                if ri.importance != importance:
                    continue
                ing = ri.ingredient
                items.append({
                    "id": ing.id,
                    "name": ing.name,
                    "is_selected": ing.id in selected_set,
                })
            return {
                "title": title,
                "items": items,
            }

        featured.ingredient_groups = [
            build_group("Required", Importance.REQUIRED),
            build_group("Secondary", Importance.SECONDARY),
            build_group("Optional", Importance.OPTIONAL),
        ]

        # Quick counters for the UI (optional but useful)
        featured.matched_count = sum(1 for ri in recipe_items if ri.ingredient_id in selected_set)
        featured.missing_count = len(recipe_items) - featured.matched_count

        # existing annotated fields (if present on queryset)
        # required_total, required_matched, missing_required are provided by scoring annotation
        more = recipes.exclude(id=featured.id)
        return featured, more
