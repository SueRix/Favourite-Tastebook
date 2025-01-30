from django.core.management.base import BaseCommand
from ..utils import import_ingredients

class Command(BaseCommand):
    help = "Importing from ingredients.csv"

    def handle(self, *args, **kwargs):
        import_ingredients("ingredients.csv")
