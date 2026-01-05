from recipe_manager.domain.exceptions.services import EmptyIngredientsError
from recipe_manager.models import Recipe
from recipe_manager.services.recipe_selection_service import annotate_recipe_scores


def search_recipes_by_ingredients(*, selected_ids, strict_required, weights=None):
    if not selected_ids:
        raise EmptyIngredientsError("List of ingredients cannot be empty for search.")

    qs = annotate_recipe_scores(
        qs=Recipe.objects.select_related("cuisine"),
        selected_ids=selected_ids,
        weights=weights,
    )

    qs = qs.filter(missing_required=0) if strict_required else qs.filter(total_matches__gt=0)

    return qs.order_by("-score", "missing_required", "-required_matched", "cook_time", "title")
