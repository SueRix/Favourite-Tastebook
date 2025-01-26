from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

class AuthenticationTests(TestCase):

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form')

    def test_register_view_post(self):
        response = self.client.post(reverse('register'), {
            'username': 'testuser123',
            'password1': 'baba12345',
            'password2': 'baba12345',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser123').exists())
        self.assertRedirects(response, reverse('home_page'))
        self.assertEqual(response.status_code, 404)


    def test_register_view_post_invalid_credentials(self):
        response = self.client.post(reverse('register'), {
            'username': 'invalid-testuser123',
            'password': 'baba12345',
            'confirm_password': 'baba12345',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='invalid-testuser123').exists())


    def test_register_view_invalid_credentials(self):
        self.user = User.objects.create_user(username='testuser')


    def test_login_view(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('home_page'))

    def test_logout_view(self):
        response = self.client.post(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_invalid_credentials_view(self):

        response = self.client.get(reverse('login'), {
            'username': 'wrong_user',
            'password': 'password123456_wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

