from recipe_manager.domain.exceptions.selectors import EmptyQueryValueError
from recipe_manager.domain.exceptions.services import EmptyIngredientsError
from recipe_manager.models import Recipe
from recipe_manager.services.recipe_selection_service import annotate_recipe_scores


def search_recipes_by_ingredients(*, selected_ids, strict_required, weights=None):
    # Guard against "bad query" shapes like: ["", "12"] / [None, 12] / "..."
    if selected_ids is None:
        raise EmptyQueryValueError("Query parameter 'ingredient' was provided as empty.")

    try:
        selected_ids = list(selected_ids)
    except TypeError:
        raise EmptyQueryValueError("Query parameter 'ingredient' must be a list-like value.")

    if any(v is None or (isinstance(v, str) and not v.strip()) for v in selected_ids):
        raise EmptyQueryValueError("Query parameter 'ingredient' contains an empty value.")

    # Normal business-rule guard (operation needs at least one ingredient)
    if not selected_ids:
        raise EmptyIngredientsError("List of ingredients cannot be empty for search.")

    qs = annotate_recipe_scores(
        qs=Recipe.objects.select_related("cuisine"),
        selected_ids=selected_ids,
        weights=weights,
    )

    qs = qs.filter(missing_required=0) if strict_required else qs.filter(total_matches__gt=0)

    return qs.order_by("-score", "missing_required", "-required_matched", "cook_time", "title")
