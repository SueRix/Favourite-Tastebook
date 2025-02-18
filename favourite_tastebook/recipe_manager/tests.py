from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser1', password='bar000')

    def test_index_view(self):
        response = self.client.get(reverse('welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_product_features_view(self):
        response = self.client.get(reverse('product_features'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'product_features.html')

    def test_home_view_authenticated(self):
        self.client.login(username='test1', password='bar000')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)

    def test_home_view_unauthenticated(self):
        response = self.client.get(reverse('home'))
        self.assertNotEqual(response.status_code, 200)

    def test_filter_recipes_no_ingredients(self):
        response = self.client.get(reverse('filter_recipes'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'error': 'No ingredients selected'})


    def test_filter_recipes_with_non_matching_ingredients(self):
        response = self.client.get(reverse('filter_recipes'), {'ingredients': 'Stone'})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'recipes': []})
