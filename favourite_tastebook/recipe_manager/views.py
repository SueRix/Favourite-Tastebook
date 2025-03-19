import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from .models import Ingredient, Recipe, RecipeIngredient, UserIngredients


class IndexView(TemplateView):
    template_name = 'index.html'


class ProductFeaturesView(TemplateView):
    template_name = 'product_features.html'


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'
    extra_context = {'ingredients': Ingredient.objects.order_by('name')}


class FilterRecipesView(View):
    def get(self, request):
        selected_ingredients = self._parse_ingredients(request)

        if not selected_ingredients:
            return JsonResponse({'error': 'No ingredients selected'})

        recipes = self._get_filtered_recipes(selected_ingredients)
        return JsonResponse({'recipes': list(recipes)})

    @staticmethod
    def _parse_ingredients(request):
        ingredient_names = request.GET.get('ingredients', '')
        return list(filter(None, map(str.strip, ingredient_names.split(','))))

    @staticmethod
    def _get_filtered_recipes(selected_ingredients):
        queryset = Recipe.objects.all()
        recipes_with_scores = []

        for recipe in queryset:
            recipe_score = 0
            recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe).select_related('ingredient')
            missing_ingredients = []

            for recipe_ingredient in recipe_ingredients:
                if recipe_ingredient.ingredient.name in selected_ingredients:
                    recipe_score += recipe_ingredient.weight
                else:
                    missing_ingredients.append(recipe_ingredient.ingredient.name)

            recipes_with_scores.append(
                {'recipe': recipe, 'score': recipe_score, 'missing_ingredients': missing_ingredients})

        recipes_with_scores.sort(key=lambda item: item['score'], reverse=True)

        formatted_recipes = []
        for item in recipes_with_scores:
            recipe = item['recipe']
            recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe).select_related('ingredient')
            if item['score'] > 0:
                formatted_recipes.append({
                    'name': recipe.name,
                    'cook_time': recipe.cook_time,
                    'instructions': recipe.instructions,
                    'ingredient_match_score': item['score'],
                    'ingredients': [ri.ingredient.name for ri in recipe_ingredients],
                })

        return formatted_recipes


class FavoriteIngredientView(LoginRequiredMixin,
                             View):  # FIXME: match not working/create match with using default ingredients + some favourite
    def get(self, request, *args, **kwargs):
        favorite_ingredients = UserIngredients.objects.filter(user=request.user).select_related('ingredients')
        favorite_ingredients_list = [
            {'name': fav.ingredients.name, 'id': fav.ingredients.id} for fav in favorite_ingredients
        ]
        return JsonResponse({'favorite_ingredients': favorite_ingredients_list})

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        ingredient_id = data.get('ingredient_id')
        action = data.get('action')

        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
        except Ingredient.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Ingredient not found'}, status=404)

        if action == 'add':
            UserIngredients.objects.get_or_create(user=request.user, ingredients=ingredient)
        elif action == 'remove':
            UserIngredients.objects.filter(user=request.user, ingredients=ingredient).delete()
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)

        return JsonResponse({'status': 'success'})


class SearchIngredientsView(View):
    @staticmethod
    def get(request):
        query = request.GET.get('q', '').strip().lower()
        mode = request.GET.get('mode', 'list')
        category = request.GET.get('category')

        if mode == 'categories':
            if category:
                ingredients = Ingredient.objects.filter(category=category, name__icontains=query).order_by('name').values('id', 'name', 'category')
                return JsonResponse({'ingredients': list(ingredients)})
            else:
                categories = Ingredient.objects.filter(category__icontains=query).values_list('category', flat=True).distinct()
                sorted_categories = sorted(list(categories))
                return JsonResponse({'categories': sorted_categories})
        else:
            ingredients = Ingredient.objects.filter(name__icontains=query).order_by('name').values('id', 'name', 'category')
            return JsonResponse({'ingredients': list(ingredients)})


# 05.03.2025 17:50 - 31.03.2025

# TODO: create feature of alphabet filtering p1 - //completed!!!
# TODO: read about pagination p2 - //completed!!!
# TODO: create search of ingredients feature - //completed!!!
# TODO: create filter of lists chosen ingredients p1 - //completed!!!
# TODO: recreate 3 types of recommendations:
# 1)full match with full ingredients, p1
# 2)full match with main ingredients, p2
# 3)partial match with main ingredients - with only 1 lack of main ingredients p3
# TODO: create deletion of selected ingredients from main list  p3
# TODO: create model of cuisines for filtering recipes p2
# TODO: recreate search from UI to BE - completed!!!
