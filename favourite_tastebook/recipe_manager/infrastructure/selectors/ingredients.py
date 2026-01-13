from recipe_manager.models import Ingredient


class IngredientSelector:
    @classmethod
    def list_categories(cls):
        return Ingredient.objects.values_list("category", flat=True).distinct().order_by("category")

    @classmethod
    def list_ingredients(cls, filters: dict):
        qs = Ingredient.objects.all()

        if q := filters.get("q"):
            qs = qs.filter(name__icontains=q)

        if category := filters.get("category"):
            qs = qs.filter(category=category)

        return qs.order_by("category", "name")

    @classmethod
    def list_selected(cls, filters: dict):
        qs = filters.get("ingredient")
        return qs.order_by("name") if qs else Ingredient.objects.none()