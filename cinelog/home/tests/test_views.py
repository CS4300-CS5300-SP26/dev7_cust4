from django.test import TestCase
from home.models import CarouselImage
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomLogInViewTest(TestCase):
    """
    Tests that the carousel images are passed to the login page.
    """
    def setUp(self):       
        """
        Set up a valid carousel image that can be used by the tests.
        """
        self.carousel_img = CarouselImage.objects.create(
            title='test123', 
            image='carousel/img.jpg'
        )
    

    def test_login_responds_with_carousel_images(self):
        """
        Test that the login function returns the movies for a carousel.
        """
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertIn("carousel_imgs", response.context)

    def test_login_valid_account(self):
        """
        Test that a user with an account can login.
        """

        data = {
            "username": "user1",
            "password": "Test.1234!!",
        }
        initial_user_count = User.objects.count()
        user, created = User.objects.get_or_create(username="user1")
        if created:
            user.set_password("Test.1234!!")
            user.save()

        response = self.client.post(reverse("login"), data=data)
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        self.assertTrue(User.objects.filter(username=data["username"]).exists())
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_invalid_account(self):
        """
        Test that a user without an account cannot login.
        """

        data = {
            "username": "user1",
            "password": "Test.1234!!",
        }
        initial_user_count = User.objects.count()

        response = self.client.post(reverse("login"), data=data)
        self.assertEqual(User.objects.count(), initial_user_count)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class SignupTest(TestCase):
    def setUp(self):
        self.data = {
            "username": "user2",
            "password1": "Test.1234!!",
            "password2": "Test.1234!!",
        }

    def test_signup_view_valid(self):
        """
        Test that the signup page loads.
        """
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signup.html")
        self.assertIn("form", response.context)

    def test_signup_view_successful(self):
        """
        Test that a user can create an account.
        """
        initial_user_count = User.objects.count()

        response = self.client.post(reverse("signup"), data=self.data)

        self.assertRedirects(response, reverse("landing"))
        self.assertEqual(User.objects.count(), initial_user_count + 1)
        self.assertTrue(User.objects.filter(username="user2").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_signup_unsuccessful(self):
        """
        Test that user cannot sign up if username is same as another user or already have an account.
        """
        # Create user with same username.
        same_data = {
            "username": "user3",
            "password1": "password.5678",
            "password2": "password.5678"
        }

        # Create user with same username if one does not already exist.
        if not User.objects.filter(username=same_data["username"]).exists():
            User.objects.create_user(username=same_data["username"], password="Test.1234!!")
        initial_user_count = User.objects.count()

        # Try to sign up with the same data.
        response = self.client.post(reverse("signup"), data=same_data)
        self.assertEqual(User.objects.count(), initial_user_count)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    def test_signup_different_passwords(self):
        """
        Test that user cannot sign up if their passwords do not match.
        """
        not_matching_data = {
            "username": "user123",
            "password1": "Test.1234!!",
            "password2": "Test",
        }

        initial_user_count = User.objects.count()

        response = self.client.post(reverse("signup"), data=not_matching_data)
        self.assertEqual(User.objects.count(), initial_user_count)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    def test_signup_blank_username(self):
        """
        Test that user cannot sign up if they do not provide a username.
        """
        no_username_data = {
            "username": "",
            "password1": "Test.1234!!",
            "password2": "Test",
        }

        initial_user_count = User.objects.count()

        response = self.client.post(reverse("signup"), data=no_username_data)
        self.assertEqual(User.objects.count(), initial_user_count)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    def test_signup_weak_password(self):
        """
        Test that user cannot sign up if they provide a weak password.
        """
        no_username_data = {
            "username": "user12345",
            "password1": "hello",
            "password2": "hello",
        }

        initial_user_count = User.objects.count()

        response = self.client.post(reverse("signup"), data=no_username_data)
        self.assertEqual(User.objects.count(), initial_user_count)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

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
