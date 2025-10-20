from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="StrongPass123!"
        )

    def test_login_success(self):
        resp = self.client.post(reverse("login"), {
            "username": "john",
            "password": "StrongPass123!",
        })
        self.assertEqual(resp.status_code, 302)

    def test_logout(self):
        self.client.login(username="john", password="StrongPass123!")
        resp = self.client.post(reverse("logout"))
        self.assertEqual(resp.status_code, 302)

