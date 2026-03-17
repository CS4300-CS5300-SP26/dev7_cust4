from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth.models import User
from home import views


class LandingPageViewTest(TestCase):
    """Tests for the landing page view."""

    def setUp(self):
        self.client = Client()

    def test_landing_page_returns_200(self):
        """Landing page should return HTTP 200."""
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)

    def test_landing_page_uses_correct_template(self):
        """Landing page should render landing.html."""
        response = self.client.get(reverse('landing'))
        self.assertTemplateUsed(response, 'landing.html')

    def test_landing_page_accessible_without_login(self):
        """Landing page should be publicly accessible."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class URLRoutingTest(TestCase):
    """Tests for URL configuration."""

    def test_root_url_resolves_to_index(self):
        """Root URL should resolve to the index view."""
        resolver = resolve('/')
        self.assertEqual(resolver.func, views.index)

    def test_login_url_exists(self):
        """Django auth login URL should be accessible."""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)

    def test_logout_url_exists(self):
        """Django auth logout URL only allows POST (Django 4.1+)."""
        response = self.client.post('/accounts/logout/')
        self.assertIn(response.status_code, [200, 302])


class AuthenticationTest(TestCase):
    """Tests for user authentication flows."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            email='test@example.com'
        )

    def test_login_with_valid_credentials(self):
        """User should be able to log in with valid credentials."""
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'testpassword123',
        }, follow=True)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_invalid_credentials(self):
        """Login should fail with wrong password."""
        response = self.client.post('/accounts/login/', {
            'username': 'testuser',
            'password': 'wrongpassword',
        })
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_page_loads_successfully(self):
        """Login page should load with HTTP 200."""
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_user_creation(self):
        """User objects should be created correctly."""
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.check_password('testpassword123'))

    def test_logout_redirects_authenticated_user(self):
        """Authenticated user logout should succeed (200 or 302 depending on config)."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post('/accounts/logout/')
        self.assertIn(response.status_code, [200, 302])
        # User should no longer be authenticated after logout
        self.assertFalse(response.wsgi_request.user.is_authenticated)
