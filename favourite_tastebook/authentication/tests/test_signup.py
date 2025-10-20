from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class SignupTests(TestCase):
    def test_signup_success(self):
        resp = self.client.post(reverse("register"), {
            "username": "alice",
            "email": "alice@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertRedirects(resp, reverse("login"))
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_signup_duplicate_email(self):
        User.objects.create_user(username="bob", email="dup@example.com", password="xYz123456!")
        resp = self.client.post(reverse("register"), {
            "username": "bob2",
            "email": "dup@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Email is already in use.")
