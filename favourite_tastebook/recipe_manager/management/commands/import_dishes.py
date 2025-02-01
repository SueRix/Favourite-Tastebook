from django.core.management.base import BaseCommand
from ..utils import import_dishes

class Command(BaseCommand):
    help = "Importing from dishes.csv"

    def handle(self, *args, **kwargs):
        import_dishes("dishes.csv")
