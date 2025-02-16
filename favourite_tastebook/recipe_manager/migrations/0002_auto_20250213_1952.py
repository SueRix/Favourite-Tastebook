import json
import os
from django.db import migrations

def load_ingredients(apps, schema_editor):
    Ingredient = apps.get_model('recipe_manager', 'Ingredient')
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'ingredients.json')

    with open(file_path, encoding='utf-8') as f:
        data = json.load(f)
        ingredients = [Ingredient(pk=item["pk"], name=item["name"], category=item["category"]) for item in data]
        Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)

def load_recipes(apps, schema_editor):
    Recipe = apps.get_model('recipe_manager', 'Recipe')
    Ingredient = apps.get_model('recipe_manager', 'Ingredient')
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'recipes.json')

    with open(file_path, encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
            recipe = Recipe.objects.create(
                pk=item["pk"],
                name=item["name"],
                cook_time=item["cook_time"],
                instructions=item["instructions"]
            )
            ingredients = Ingredient.objects.filter(pk__in=item["ingredient_pks"])
            recipe.ingredients.set(ingredients)

def load_dishes(apps, schema_editor):
    Dish = apps.get_model('recipe_manager', 'Dish')
    Recipe = apps.get_model('recipe_manager', 'Recipe')
    file_path = os.path.join(os.path.dirname(__file__), 'data', 'dishes.json')

    with open(file_path, encoding='utf-8') as f:
        data = json.load(f)
        dishes = [Dish(pk=item["pk"], name=item["name"], recipe_id=item["recipe_pk"]) for item in data]
        Dish.objects.bulk_create(dishes, ignore_conflicts=True)

def reverse_migration(apps, schema_editor):
    Ingredient = apps.get_model('recipe_manager', 'Ingredient')
    Recipe = apps.get_model('recipe_manager', 'Recipe')
    Dish = apps.get_model('recipe_manager', 'Dish')

    Dish.objects.all().delete()
    Recipe.objects.all().delete()
    Ingredient.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('recipe_manager', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_ingredients, reverse_code=reverse_migration),
        migrations.RunPython(load_recipes, reverse_code=reverse_migration),
        migrations.RunPython(load_dishes, reverse_code=reverse_migration),
    ]
