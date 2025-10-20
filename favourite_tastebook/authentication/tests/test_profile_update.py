import tempfile, shutil
from datetime import timedelta
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
_TEMP_MEDIA = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=_TEMP_MEDIA)
class ProfileUpdateTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(
            username="mike", email="mike@example.com", password="StrongPass123!"
        )

    def test_username_change_success_first_time(self):
        self.client.login(username="mike", password="StrongPass123!")
        resp = self.client.post(reverse("profile"), {
            "action": "account",
            "username": "mike_new",
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "mike_new")

    def test_username_change_cooldown_blocked(self):
        self.client.login(username="mike", password="StrongPass123!")
        # 1-я смена — ок
        self.client.post(reverse("profile"), {"action": "account", "username": "mike_new"})
        # Попытка 2 — должна быть заблокирована
        resp = self.client.post(reverse("profile"), {"action": "account", "username": "mike_new2"})
        self.assertEqual(resp.status_code, 302)  # у тебя PRG
        self.user.refresh_from_db()
        # Ник не поменялся
        self.assertEqual(self.user.username, "mike_new")

    def test_username_change_after_30_days_ok(self):
        self.client.login(username="mike", password="StrongPass123!")
        # 1-я смена
        self.client.post(reverse("profile"), {"action": "account", "username": "mike_new"})
        # Подвинем last_username_change_at на 31 день назад
        profile = self.user.profile
        profile.last_username_change_at = timezone.now() - timedelta(days=31)
        profile.save()

        # Теперь можно снова
        resp = self.client.post(reverse("profile"), {"action": "account", "username": "mike_final"})
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "mike_final")
