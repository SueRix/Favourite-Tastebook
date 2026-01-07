from django.db import migrations
from django.core.management import call_command


def load_fixtures(apps, schema_editor):
    call_command('loaddata', 'cuisines/cuisines.json')
    call_command('loaddata', 'ingredients/01_ing.json')

    call_command('loaddata', 'recipes/01_ukrainian.json')
    call_command('loaddata', 'recipes/02_common.json')
    call_command('loaddata', 'recipes/03_italian.json')


    call_command('loaddata', 'recipe_ingredients/01_ukr.json')
    call_command('loaddata', 'recipe_ingredients/02_common.json')
    call_command('loaddata', 'recipe_ingredients/03_italian.json')


def reverse_func(apps, schema_editor):
    RecipeIngredient = apps.get_model("recipe_manager", "RecipeIngredient")
    Recipe = apps.get_model("recipe_manager", "Recipe")
    Ingredient = apps.get_model("recipe_manager", "Ingredient")
    Cuisine = apps.get_model("recipe_manager", "Cuisine")

    RecipeIngredient.objects.all().delete()
    Recipe.objects.all().delete()
    Ingredient.objects.all().delete()
    Cuisine.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('recipe_manager', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_fixtures, reverse_func),
    ]