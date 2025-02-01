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
        print(f"File {file_path} not found!")
        return

    records = []
    try:
        with open(file_path, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            required_fields = {"name", "category"}
            if not required_fields.issubset(reader.fieldnames):
                print(f"Error: CSV file missing required columns. Found: {reader.fieldnames}")
                return

            for row in reader:
                records.append(Ingredient(name=row['name'].strip(), category=row.get('category', "").strip()))

        if records:
            with transaction.atomic():
                Ingredient.objects.bulk_create(records)

            print(f"Successfully imported {len(records)} ingredients from {file_path}.")
        else:
            print("No valid ingredients found to import.")

    except Exception as e:
        print(f"Error processing file: {e}")


def import_recipes(file_name, folder_path="recipe_manager/management/database_data"):
    file_path = f"{folder_path}/{file_name}"

    if not os.path.exists(file_path):
        print(f"File {file_path} not found!")
        return

    records = []
    try:
        with open(file_path, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            required_fields = {"name", "tags", "instructions", "created_by", "cook_time", "ingredients"}
            if not required_fields.issubset(reader.fieldnames):
                print(f"Error: CSV file missing required columns. Found: {reader.fieldnames}")
                return

            for row in reader:
                try:
                    user = User.objects.get(id=row['created_by'].strip())

                    recipe = Recipe(
                        name=row['name'].strip(),
                        tags=row.get('tags', "").strip(),
                        instructions=row['instructions'].strip(),
                        created_by=user,
                        cook_time=int(row['cook_time']) if row['cook_time'].isdigit() else None
                    )
                    records.append(recipe)

                except User.DoesNotExist:
                    print(f"Warning: User with ID {row['created_by']} not found. Skipping row.")

        if records:
            with transaction.atomic():
                Recipe.objects.bulk_create(records)

            print(f"Successfully imported {len(records)} recipes from {file_path}.")
        else:
            print("No valid recipes found to import.")

    except Exception as e:
        print(f"Error processing file: {e}")


def import_dishes(file_name, folder_path="recipe_manager/management/database_data"):
    file_path = f"{folder_path}/{file_name}"

    if not os.path.exists(file_path):
        print(f"File {file_path} not found!")
        return

    records = []
    try:
        with open(file_path, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            required_fields = {"name", "recipe_id", "created_by_id"}
            if not required_fields.issubset(reader.fieldnames):
                print(f"Error: CSV file missing required columns. Found: {reader.fieldnames}")
                return

            for row in reader:
                try:
                    user = User.objects.get(id=row['created_by_id'].strip())
                    recipe = Recipe.objects.get(id=row['recipe_id'].strip())

                    records.append(Dish(name=row['name'].strip(), recipe=recipe, created_by=user))

                except User.DoesNotExist:
                    print(f"Warning: User with ID {row['created_by_id']} not found. Skipping row.")
                except Recipe.DoesNotExist:
                    print(f"Warning: Recipe with ID {row['recipe_id']} not found. Skipping row.")

        if records:
            with transaction.atomic():
                Dish.objects.bulk_create(records)

            print(f"Successfully imported {len(records)} dishes from {file_path}.")
        else:
            print("No valid dishes found to import.")

    except Exception as e:
        print(f"Error processing file: {e}")


def import_user_ingredients(file_name, folder_path="recipe_manager/management/database_data"):
    file_path = f"{folder_path}/{file_name}"

    if not os.path.exists(file_path):
        print(f"File {file_path} not found!")
        return

    records = []
    try:
        with open(file_path, "r", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)

            required_fields = {"user_id", "ingredients_id", "quantity", "unit", "created_by_id"}
            if not required_fields.issubset(reader.fieldnames):
                print(f"Error: CSV file missing required columns. Found: {reader.fieldnames}")
                return

            for row in reader:
                try:
                    user = User.objects.get(id=row['user_id'].strip())
                    ingredient = Ingredient.objects.get(id=row['ingredients_id'].strip())
                    created_by = User.objects.get(id=row['created_by_id'].strip())

                    records.append(UserIngredients(
                        user=user,
                        ingredients=ingredient,
                        quantity=int(row['quantity'].strip()) if row['quantity'].isdigit() else 0,
                        unit=row['unit'].strip(),
                        created_by=created_by
                    ))

                except User.DoesNotExist:
                    print(f"Warning: User with ID {row['user']} not found. Skipping row.")
                except Ingredient.DoesNotExist:
                    print(f"Warning: Ingredient with ID {row['ingredients']} not found. Skipping row.")

        if records:
            with transaction.atomic():
                UserIngredients.objects.bulk_create(records)

            print(f"Successfully imported {len(records)} user ingredients from {file_path}.")
        else:
            print("No valid user ingredients found to import.")

    except Exception as e:
        print(f"Error processing file: {e}")
