from django.core.management.base import BaseCommand
from ..utils import import_user_ingredients

class Command(BaseCommand):
    help = "Importing from user_ingredients.csv"

    def handle(self, *args, **kwargs):
        import_user_ingredients("user_ingredients.csv")
