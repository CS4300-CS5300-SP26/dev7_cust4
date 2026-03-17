from django.test import TestCase
from django.urls import reverse, resolve
from home import views

class URLRoutingTest(TestCase):
    """Tests for URL configuration."""

    def test_root_url_resolves_to_index(self):
        """Root URL should resolve to the index view."""
        resolver = resolve('/')
        self.assertEqual(resolver.func, views.landing_page)

    def test_login_url_exists(self):
        """Django auth login URL should be accessible."""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)

    def test_logout_url_exists(self):
        """Django auth logout URL only allows POST (Django 4.1+)."""
        response = self.client.post('/accounts/logout/')
        self.assertIn(response.status_code, [200, 302])