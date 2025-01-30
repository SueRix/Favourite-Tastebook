import csv
import os

from django.db import transaction
from django.contrib.auth.models import User
from ..models import Ingredient, Recipe, Dish, UserIngredients

# This file needed to reading of .csv files for fill PostgreSQL database.
# It is examples of kind .csv files for Models:

# ingredients.csv:
"""
name,category
Tomato,Vegetable
Chicken,Meat
"""

# recipes.csv:
"""
name,tags,instructions,created_by,cook_time,ingredients
Pasta,Italian,Boil water...,1,20,"Tomato,Garlic,Basil"
"""

# dishes.csv:
"""
name,recipe,created_by
Spaghetti,1,1
"""

# user_ingredients.csv:
"""
user,ingredients,quantity,unit,created_by
1,2,500,g,1
"""


def import_ingredients(file_name, folder_path="recipe_manager/management/database_data"):
    file_path = f"{folder_path}/{file_name}"

    if not os.path.exists(file_path):
        print(f"File {file_path} did not exist!")
        return

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        records = []

        for row in reader:
            records.append(Ingredient(name=row['name'], category=row.get('category', None)))

        with transaction.atomic():
            Ingredient.objects.bulk_create(records)

    print(f" Successfully imported {len(records)} ingredients from {file_path}.")


def import_recipes(file_name, folder_path="recipe_manager/management/database_data"):
    file_path = f"{folder_path}/{file_name}"

    if not os.path.exists(file_path):
        print(f"File {file_path} did not exist!")
        return

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        records = []

        for row in reader:
            try:
                user = User.objects.get(id=row['created_by'])
            except User.DoesNotExist:
                print(f"User with ID {row['created_by']} not found. Skipping...")
                continue

            recipe = Recipe(
                name=row['name'],
                tags=row.get('tags', None),
                instructions=row['instructions'],
                created_by=user,
                cook_time=int(row['cook_time']) if row.get('cook_time') else None
            )
            recipe.save()

            ingredient_names = row['ingredients'].split(",")
            for ing_name in ingredient_names:
                ingredient = Ingredient.objects.filter(name=ing_name.strip()).first()
                if ingredient:
                    recipe.ingredients.add(ingredient)
                else:
                    print(f"⚠ Ingredient '{ing_name.strip()}' not found. Skipping...")

            records.append(recipe)

    print(f"Successfully imported {len(records)} recipes from {file_path}.")



# def import_dishes(file_path):
#     with open(file_path, newline='', encoding='utf-8') as csvfile:
#         reader = csv.DictReader(csvfile)
#         records = []
#         for row in reader:
#             user = User.objects.get(id=row['created_by'])
#             recipe = Recipe.objects.get(id=row['recipe'])
#             records.append(Dish(name=row['name'], recipe=recipe, created_by=user))
#
#         with transaction.atomic():
#             Dish.objects.bulk_create(records)
#     print(f"Successfully imported {len(records)} dishes.")
#
#
# def import_user_ingredients(file_path):
#     with open(file_path, newline='', encoding='utf-8') as csvfile:
#         reader = csv.DictReader(csvfile)
#         records = []
#         for row in reader:
#             user = User.objects.get(id=row['user'])
#             ingredient = Ingredient.objects.get(id=row['ingredients'])
#             created_by = User.objects.get(id=row['created_by'])
#             records.append(UserIngredients(
#                 user=user,
#                 ingredients=ingredient,
#                 quantity=int(row['quantity']),
#                 unit=row['unit'],
#                 created_by=created_by
#             ))
#
#         with transaction.atomic():
#             UserIngredients.objects.bulk_create(records)
#     print(f"Successfully imported {len(records)} user ingredients.")

