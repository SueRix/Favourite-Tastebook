import json

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
    extra_context = {'ingredients': Ingredient.objects.all()}


class FilterRecipesView(View):
    @staticmethod
    def get(request):
        ingredient_names = request.GET.get('ingredients', '')
        ingredient_names = list(filter(None, map(str.strip, ingredient_names.split(','))))

        if not ingredient_names:
            recipes_qs = Recipe.objects.values('name', 'cook_time', 'instructions')
        else:
            recipes_qs = (
                Recipe.objects
                .annotate(
                    matching_ingredients=Count(
                        'ingredients',
                        distinct=True,
                        filter=Q(ingredients__name__in=ingredient_names)
                    )
                )
                .filter(matching_ingredients=len(ingredient_names))
                .values('name', 'cook_time', 'instructions'))

        return JsonResponse({'recipes': list(recipes_qs)})
