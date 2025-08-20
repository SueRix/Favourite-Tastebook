from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='baba12345')

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

    def test_register_view_invalid_password_credentials_post(self):
        response = self.client.post(reverse('register'), {
            'username': 'invalid-testuser',
            'password1': 'baba123',
            'password2': 'baba1234567',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The two password fields didn’t match.')
        self.assertFalse(User.objects.filter(email='invalid-testuser123').exists())

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form')


    def test_login_view_post(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'baba12345'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))


    def test_login_invalid_credentials_view_post(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'password123_wrong',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login.html')

    def test_logout_view(self):
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
