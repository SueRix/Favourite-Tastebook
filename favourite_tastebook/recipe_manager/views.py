import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from .models import Ingredient, Recipe


class IndexView(TemplateView):
    template_name = 'index.html'

class OurProductView(TemplateView):
    template_name = 'our_product.html'

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'
    extra_context = {'ingredients': Ingredient.objects.all()}

class FilterRecipesView(View):
    def post(self, request):
        data = json.loads(request.body)
        ingredient_names = data.get('ingredients', [])

        recipes_qs = Recipe.objects.all()
        ingredients_qs = Ingredient.objects.filter(name__in=ingredient_names)
        for ing in ingredients_qs:
            recipes_qs = recipes_qs.filter(ingredients=ing)

        results = []
        for r in recipes_qs:
            results.append({
                'name': r.name,
                'cook_time': r.cook_time,
                'instructions': r.instructions,
            })
        return JsonResponse({'recipes': results})

    def get(self):
        return JsonResponse({'error': 'Only POST allowed'}, status=405)