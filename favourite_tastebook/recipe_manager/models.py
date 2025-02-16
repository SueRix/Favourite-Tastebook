from django.db import models
from django.contrib.auth.models import User


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, null=True, blank=True)


class Recipe(models.Model):
    name = models.CharField(max_length=100, unique=True)
    ingredients = models.ManyToManyField(Ingredient, related_name='recipes')
    instructions = models.TextField()
    cook_time = models.IntegerField(help_text = "Time in minutes", null=True, blank=True)

class Dish(models.Model):
    name = models.CharField(max_length=100)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='dishes')


class UserIngredients(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredients = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    unit = models.CharField(max_length=100)