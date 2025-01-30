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



