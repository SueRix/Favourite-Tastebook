from recipe_manager.models import Ingredient


def get_ingredient_categories():
    return Ingredient.objects.values_list("category", flat=True).distinct().order_by("category")


def get_ingredients(q=None, category=None):
    filters = {}
    if q:
        filters["name__icontains"] = q
    if category:
        filters["category"] = category

    return Ingredient.objects.filter(**filters).order_by("category", "name")

