from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="kate",
            email="kate@example.com",
            password="OldPass123!"
        )

    def test_password_change_requires_auth(self):
        resp = self.client.get(reverse("password_change"))
        self.assertEqual(resp.status_code, 302)

    def test_password_change_flow(self):
        self.client.login(username="kate", password="OldPass123!")
        resp = self.client.post(reverse("password_change"), {
            "old_password": "OldPass123!",
            "new_password1": "NewPass456!",
            "new_password2": "NewPass456!",
        })
        self.assertRedirects(resp, reverse("password_change_done"))
        self.client.logout()
        ok = self.client.login(username="kate", password="NewPass456!")
        self.assertTrue(ok)
