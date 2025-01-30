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

    if not file_path or not file_name:
        print("Invalid file path or file name!")
        return

    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            records = [Ingredient(name=row['name'], category=row.get('category', None)) for row in reader]

        if records:
            with transaction.atomic():
                Ingredient.objects.bulk_create(records)

        print(f" Successfully imported {len(records)} ingredients from {file_path}.")

    except FileNotFoundError:
        print(f"File {file_path} not found!")


def import_recipes(file_name, folder_path="recipe_manager/management/database_data"):
    file_path = f"{folder_path}/{file_name}"

    if not file_path or not file_name:
        print("Invalid file path or file name!")
        return

    try:
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

                if 'ingredients' in row and row['ingredients']:
                    ingredient_names = row['ingredients'].split(",")
                    for ing_name in ingredient_names:
                        ingredient = Ingredient.objects.filter(name=ing_name.strip()).first()
                        if ingredient:
                            recipe.ingredients.add(ingredient)
                        else:
                            print(f"Ingredient '{ing_name.strip()}' not found. Skipping...")

                records.append(recipe)

        print(f"Successfully imported {len(records)} recipes from {file_path}.")

    except FileNotFoundError:
        print(f"File {file_path} not found!")




