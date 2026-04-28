from recipe_manager.domain.services.taste_vector_engine import TasteVectorModel
from recipe_manager.infrastructure.selectors.ingredients import IngredientSelector
from recipe_manager.infrastructure.orm.recipe_search import RecipeSearchORM
from recipe_manager.infrastructure.presentation.featured_recipe import FeaturedRecipePresenter
from recipe_manager.models import SavedRecipe, UserTastePreference


class DashboardUseCase:

    @classmethod
    def build_home(cls, filters, user=None):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        return {
            "categories": IngredientSelector.list_categories(),
            "ingredients": IngredientSelector.list_ingredients(filters),
            "selected_ingredients": selected,
            "selected_ids": selected_ids,
            "selected_count": len(selected_ids),
            "recipes": RecipeSearchORM.find_recipes(filters, user=user),
        }

    @classmethod
    def _build_ingredients_context(cls, ingredients_queryset, filters):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        return {
            "ingredients": ingredients_queryset,
            "selected_ingredients": selected,
            "selected_ids": selected_ids,
            "selected_count": len(selected_ids),
        }

    @classmethod
    def build_ingredients_partial(cls, filters):
        qs = IngredientSelector.list_ingredients(filters)
        return cls._build_ingredients_context(qs, filters)

    @classmethod
    def build_tastes_profile(cls, user):
        """
        builds context for the user tastes profile page.
        """
        from recipe_manager.models import Ingredient, UserTastePreference

        ingredients = Ingredient.objects.all().order_by("category", "name")

        user_prefs = UserTastePreference.objects.filter(
            user=user,
            is_explicit=True
        ).values_list('ingredient_id', 'score')

        prefs_dict = {ing_id: score for ing_id, score in user_prefs}

        return {
            "ingredients": ingredients,
            "user_tastes": prefs_dict,
        }

    @classmethod
    def build_recipes_partial(cls, filters, user, auto_show=False):
        selected = IngredientSelector.list_selected(filters)
        selected_ids = list(selected.values_list("id", flat=True))

        recipes_qs = RecipeSearchORM.find_recipes(filters, user=user)

        use_tastes = filters.get("use_tastes") in ["on", "1", "true", True]

        recipes_list = list(recipes_qs)

        if user.is_authenticated and use_tastes and recipes_list:
            user_prefs = UserTastePreference.objects.filter(user=user).exclude(score=-2)
            user_weights = {pref.ingredient_id: pref.score for pref in user_prefs}

            if user_weights:
                recipes_data = []
                for recipe in recipes_list:
                    recipes_data.append({
                        'recipe_obj': recipe,
                        'ingredient_ids': [ri.ingredient_id for ri in recipe.ingredients.all()],
                        'base_score': getattr(recipe, 'score', 0),
                        'tier': getattr(recipe, 'relevance_tier', 3)
                    })

                ranked_data = TasteVectorModel.rank_by_tastes(recipes_data, user_weights)
                recipes_list = [item['recipe_obj'] for item in ranked_data]

        saved_recipe_ids = set()
        if user.is_authenticated:
            saved_recipe_ids = set(SavedRecipe.objects.filter(user=user).values_list('recipe_id', flat=True))

        is_ai_mode = IngredientSelector.is_ai_mode(filters)
        effective_auto_show = auto_show or is_ai_mode

        featured, tier_1, tier_2 = FeaturedRecipePresenter.select(
            recipes_list,
            recipe_id=filters.get("recipe"),
            selected_ids=selected_ids,
            saved_ids=saved_recipe_ids,
            auto_show=effective_auto_show
        )

        return {
            "selected_count": len(selected_ids),
            "featured": featured,
            "tier_1_recipes": tier_1,
            "tier_2_recipes": tier_2,
            "is_ai_mode": is_ai_mode,
        }
