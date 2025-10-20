import tempfile, shutil
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

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

    def test_profile_update_basic(self):
        self.client.login(username="mike", password="StrongPass123!")

        resp = self.client.post(reverse("profile"), {
            "action": "account",
            "username": "mike",
            "email": "mike_new@example.com",
        })
        self.assertEqual(resp.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "mike_new@example.com")

        resp = self.client.post(reverse("profile"), {
            "action": "profile",
            "display_name": "Mike D",
            "country": "UA",
        })
        self.assertEqual(resp.status_code, 302)

    def test_profile_update_duplicate_email(self):
        User.objects.create_user(username="other", email="dup@example.com", password="xYz123456!")
        self.client.login(username="mike", password="StrongPass123!")

        resp = self.client.post(reverse("profile"), {
            "action": "account",
            "username": "mike",
            "email": "dup@example.com",
        })

        self.assertEqual(resp.status_code, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "mike@example.com")
