from django.core.management.base import BaseCommand
from ..utils import import_recipes

class Command(BaseCommand):
    help = "Importing from recipes.csv"

    def handle(self, *args, **kwargs):
        import_recipes("recipes.csv")
