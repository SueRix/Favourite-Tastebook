from django.db.models import Q
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
        form_qs = filters.get("ingredient", Ingredient.objects.none())
        if hasattr(form_qs, "query"):
            ingredient_ids = list(form_qs.values_list("id", flat=True))
        else:
            ingredient_ids = filters.getlist("ingredient") if hasattr(filters, "getlist") else []

        ai_names = filters.getlist("ai_selected") if hasattr(filters, "getlist") else filters.get("ai_selected", [])

        if not ingredient_ids and not ai_names:
            return Ingredient.objects.none()

        query = Q()
        if ingredient_ids:
            query |= Q(id__in=ingredient_ids)
        if ai_names:
            query |= Q(name__in=ai_names)

        return Ingredient.objects.filter(query).distinct().order_by("name")

    @classmethod
    def search_by_name(cls, query, category=None):
        qs = Ingredient.objects.all()
        if category:
            qs = qs.filter(category=category)

        if not query:
            return qs.order_by("category", "name")

        return qs.filter(name__icontains=query).order_by("category", "name")