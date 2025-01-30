from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Creating 10 users"

    def handle(self, *args, **kwargs):
        users_created = 0
        for i in range(1, 11):
            user, created = User.objects.get_or_create(
                username=f"user{i}",
                defaults={"email": f"user{i}@example.com", "password": "password123"}
            )
            if created:
                users_created += 1

        self.stdout.write(self.style.SUCCESS(f"Added 10 users!"))
