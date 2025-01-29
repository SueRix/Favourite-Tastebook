import csv
from django.db import transaction
from django.contrib.auth.models import User
from models import Ingredient, Recipe, Dish, UserIngredients

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

#dishes.csv:
"""
name,recipe,created_by
Spaghetti,1,1
"""

#user_ingredients.csv:
"""
user,ingredients,quantity,unit,created_by
1,2,500,g,1
"""

#TODO: Create CRUD functions for every model.
def import_ingredients(file_path):
    pass

def import_recipes(file_path):
    pass

def import_dishes(file_path):
    pass

def import_user_ingredients(file_path):
    pass