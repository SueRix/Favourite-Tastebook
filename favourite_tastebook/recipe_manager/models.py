from django.db import models
from django.contrib.auth.models import User


class Ingredient(models.Model):
    objects = models.Manager
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, null=True, blank=True)


class Recipe(models.Model):
    objects = models.Manager
    name = models.CharField(max_length=100, unique=True)
    instructions = models.TextField()
    cook_time = models.IntegerField(help_text = "Time in minutes", null=True, blank=True)

class RecipeIngredient(models.Model):
    objects = models.Manager
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    weight = models.IntegerField(default=1)

    class Meta:
        unique_together = ('recipe', 'ingredient')


class Dish(models.Model):
    objects = models.Manager
    name = models.CharField(max_length=100)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='dishes')


class UserIngredients(models.Model):
    objects = models.Manager
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredients = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    unit = models.CharField(max_length=100)