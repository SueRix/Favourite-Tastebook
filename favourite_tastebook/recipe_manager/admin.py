from django.contrib import admin
from .models import Recipe

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "cuisine")
    fields = ("title", "cuisine", "description", "image_url")
