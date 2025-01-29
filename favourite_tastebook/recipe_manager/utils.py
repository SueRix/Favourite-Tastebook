# This file needed to reading of .csv files for fill PostgreSQL database.

# It is example of kind .csv table for Models:

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