from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from .models import Ingredient, Recipe


class IndexView(TemplateView):
    template_name = 'index.html'


class ProductFeaturesView(TemplateView):
    template_name = 'product_features.html'


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'
    extra_context = {'ingredients': Ingredient.objects.order_by('name')}


class FilterRecipesView(View):
    def get(self, request):
        ingredients = self._parse_ingredients(request)

        if not ingredients:
            return JsonResponse({'error': 'No ingredients selected'})

        recipes = self._get_filtered_recipes(ingredients)
        return JsonResponse({'recipes': list(recipes)})

    @staticmethod
    def _parse_ingredients(request):
        ingredient_names = request.GET.get('ingredients', '')
        return list(filter(None, map(str.strip, ingredient_names.split(','))))

    @staticmethod
    def _get_filtered_recipes(ingredients):
        query = Recipe.objects.values('name', 'cook_time', 'instructions')

        if ingredients:
            query = Recipe.objects.filter(ingredients__name__in=ingredients).distinct().values('name', 'cook_time',
                                                                                               'instructions')

#TODO: create feature of alphabet filtering p1 - //completed!!!
#TODO: read about pagination p2 - //completed!!!
#TODO: create search of ingredients feature - //completed!!!
#TODO: create filter of lists chosen ingredients p1
#TODO: recreate 3 types of recommendations:
# 1)full match with full ingredients, p1
# 2)full match with main ingredients, p2
# 3)partial match with main ingredients - with only 1 lack of main ingredients p3
#TODO: create deletion of selected ingredients from main list  p3
#TODO: create model of cuisines for filtering recipes p2

# 05.03.2025 17:50 - 31.03.2025
