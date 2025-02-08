import json

def load_ingredients(apps, json_path):
    """
    Загрузка данных в модель Ingredient:
    JSON-формат: [ { "pk": 1, "name": "...", "category": "..." }, ... ]
    """
    Ingredient = apps.get_model('recipe_manager', 'Ingredient')
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        Ingredient.objects.update_or_create(
            pk=item['pk'],
            defaults={
                'name': item['name'],
                'category': item.get('category', None),
            }
        )

def load_recipes(apps, json_path):
    """
    Загрузка данных в модель Recipe:
    JSON-формат:
    [
      {
        "pk": 1, "name": "...",
        "cook_time": ...,
        "instructions": "...",
        "ingredient_pks": [1, 2, 3]
      }
    ]
    """
    Recipe = apps.get_model('recipe_manager', 'Recipe')
    Ingredient = apps.get_model('recipe_manager', 'Ingredient')

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        recipe, _ = Recipe.objects.update_or_create(
            pk=item['pk'],
            defaults={
                'name': item['name'],
                'cook_time': item['cook_time'],
                'instructions': item['instructions'],
            }
        )
        # Привязываем ManyToMany ингредиенты
        if 'ingredient_pks' in item:
            ing_qs = Ingredient.objects.filter(pk__in=item['ingredient_pks'])
            recipe.ingredients.set(ing_qs)

def load_dishes(apps, json_path):
    """
    Загрузка данных в модель Dish:
    JSON-формат: [ { "pk": 1, "name": "...", "recipe_pk": 1 }, ... ]
    """
    Dish = apps.get_model('recipe_manager', 'Dish')
    Recipe = apps.get_model('recipe_manager', 'Recipe')

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        recipe_obj = Recipe.objects.get(pk=item['recipe_pk'])
        Dish.objects.update_or_create(
            pk=item['pk'],
            defaults={
                'name': item['name'],
                'recipe': recipe_obj
            }
        )
