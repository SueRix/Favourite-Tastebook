from recipe_manager.models import Recipe, SavedRecipe
from recipe_manager.domain.enums import TasteLevels, Importance
from recipe_manager.models import Ingredient, Cuisine, UserTastePreference, UserCuisinePreference
from recipe_manager.infrastructure.selectors.ingredients import IngredientSelector

class TasteManagementUseCase:
    """
    logic for updating user tastes based on positive feedback (likes).
    """

    @classmethod
    def apply_recipe_like(cls, user, recipe_id: int, only_required: bool = True):
        # 1. handle the saved recipe state (mark as favorite)
        saved_recipe, _ = SavedRecipe.objects.get_or_create(
            user=user,
            recipe_id=recipe_id
        )

        # if already explicitly liked, do nothing to prevent spamming the db
        if saved_recipe.is_favorite:
            return

        saved_recipe.is_favorite = True
        saved_recipe.save()

        # 2. fetch recipe with ingredients to apply implicit feedback
        try:
            recipe = Recipe.objects.prefetch_related('ingredients').get(id=recipe_id)
        except Recipe.DoesNotExist:
            return

        # filter ingredients by importance if only_required is true
        if only_required:
            ingredient_ids = [
                ri.ingredient_id
                for ri in recipe.ingredients.all()
                if ri.importance == Importance.REQUIRED
            ]
        else:
            ingredient_ids = [ri.ingredient_id for ri in recipe.ingredients.all()]

        # 3. protect explicit manual user choices from being overwritten
        explicit_ids = set(UserTastePreference.objects.filter(
            user=user,
            ingredient_id__in=ingredient_ids,
            is_explicit=True
        ).values_list('ingredient_id', flat=True))

        # 4. update weights for ingredients the user hasn't explicitly rated
        for ing_id in ingredient_ids:
            if ing_id in explicit_ids:
                continue

            pref, created = UserTastePreference.objects.get_or_create(
                user=user,
                ingredient_id=ing_id,
                defaults={'score': TasteLevels.LIKE, 'is_explicit': False}
            )

            # upgrade neutral/dislike to like if it was set implicitly before
            if not created and not pref.is_explicit and pref.score < TasteLevels.LIKE:
                pref.score = TasteLevels.LIKE
                pref.save()

    @classmethod
    def remove_recipe_like(cls, user, recipe_id: int):
        """
        optional: logic if user un-likes a recipe.
        simply toggles the favorite flag.
        reversing implicit ingredient weights is too complex and usually not needed.
        """
        SavedRecipe.objects.filter(user=user, recipe_id=recipe_id).update(is_favorite=False)

    @classmethod
    def update_ingredient_taste(cls, user, ingredient_id: int, score: int):
        """
        updates or creates an explicit user preference for a specific ingredient.
        """
        from recipe_manager.models import UserTastePreference

        UserTastePreference.objects.update_or_create(
            user=user,
            ingredient_id=ingredient_id,
            defaults={'score': score, 'is_explicit': True}
        )

    @classmethod
    def build_tastes_profile(cls, user):


        ingredients = list(Ingredient.objects.all().order_by("category", "name"))
        user_prefs = UserTastePreference.objects.filter(
            user=user,
            is_explicit=True
        ).values_list('ingredient_id', 'score')
        prefs_dict = {ing_id: score for ing_id, score in user_prefs}

        cuisines = list(Cuisine.objects.all().order_by("name"))
        cuisine_prefs = UserCuisinePreference.objects.filter(
            user=user
        ).values_list('cuisine_id', 'score')
        cuisine_prefs_dict = {c_id: score for c_id, score in cuisine_prefs}

        for ing in ingredients:
            ing.current_score = prefs_dict.get(ing.id, 0)

        for cui in cuisines:
            cui.current_score = cuisine_prefs_dict.get(cui.id, 0)

        return {
            "ingredients": ingredients,
            "categories": IngredientSelector.list_categories(),
            "cuisines": cuisines,
            "cuisine_tastes": cuisine_prefs_dict,
            "has_rated_ingredients": any(score != 0 for score in prefs_dict.values()),
            "has_rated_cuisines": any(score != 0 for score in cuisine_prefs_dict.values()),
        }

    @classmethod
    def update_cuisine_taste(cls, user, cuisine_id: int, score: int):
        from recipe_manager.models import UserCuisinePreference

        UserCuisinePreference.objects.update_or_create(
            user=user,
            cuisine_id=cuisine_id,
            defaults={'score': score}
        )