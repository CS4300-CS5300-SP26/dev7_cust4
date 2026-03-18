from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomLogInViewTest(TestCase):
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

        self.assertRedirects(response, reverse("movies"))
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

from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

# create a movie to test with
MOCK_MOVIE = {
    "id": 550,
    "title": "Fight Club",
    "overview": "A depressed man forms an underground fight club.",
    "release_date": "1999-10-15",
    "vote_average": 8.438,
    "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    "backdrop_path": "/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
    "runtime": 139,
    "genres": [{"id": 18, "name": "Drama"}],
    "credits": {
        "cast": [
            {"name": "Brad Pitt", "character": "Tyler Durden", "profile_path": "/abc.jpg"},
            {"name": "Edward Norton", "character": "The Narrator", "profile_path": "/xyz.jpg"},
        ],
        "crew": [
            {"name": "David Fincher", "job": "Director", "profile_path": "/dir.jpg"},
        ]
    }
}

MOCK_MOVIES_LIST = [MOCK_MOVIE]


class MoviesViewTest(TestCase):
    """Tests for the movies listing page."""

    def setUp(self):
        self.client = Client()
        # patch once for all tests in this class
        self.mock_fetch = patch("home.views.fetch_movies", return_value=MOCK_MOVIES_LIST).start()
        self.addCleanup(patch.stopall)  # stops all patches after each test automatically

    def test_movies_page_returns_200(self):
        """Movies page should return HTTP 200."""
        response = self.client.get(reverse("movies"))
        self.assertEqual(response.status_code, 200)

    def test_movies_page_uses_correct_template(self):
        """Movies page should render movies.html."""
        response = self.client.get(reverse("movies"))
        self.assertTemplateUsed(response, "movies.html")

    def test_movies_page_accessible_without_login(self):
        """Movies page should be publicly accessible."""
        response = self.client.get(reverse("movies"))
        self.assertEqual(response.status_code, 200)

    def test_movies_page_passes_all_three_categories(self):
        """Movies page should pass popular, top_rated, and now_playing to context."""
        response = self.client.get(reverse("movies"))
        self.assertIn("movies", response.context)
        self.assertIn("top_rated_movies", response.context)
        self.assertIn("now_playing_movies", response.context)

    def test_movies_page_context_contains_movie_data(self):
        """Movies context should contain movie list data."""
        response = self.client.get(reverse("movies"))
        self.assertEqual(len(response.context["movies"]), 1)
        self.assertEqual(response.context["movies"][0]["title"], "Fight Club")

    def test_movies_page_handles_empty_api_response(self):
        """Movies page should handle empty list from API without crashing."""
        self.mock_fetch.return_value = []
        response = self.client.get(reverse("movies"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["movies"]), [])


class MovieDetailViewTest(TestCase):
    """Tests for the movie detail page."""

    def setUp(self):
        self.client = Client()
        # patch all three once for the whole class
        self.mock_fetch  = patch("home.views.fetch_movie_detail", return_value=MOCK_MOVIE.copy()).start()
        self.mock_cast = patch("home.views.get_cast", return_value=MOCK_MOVIE["credits"]["cast"]).start()
        self.mock_director = patch("home.views.get_director", return_value=MOCK_MOVIE["credits"]["crew"][0]).start()
        self.addCleanup(patch.stopall)

    def test_movie_detail_returns_200(self):
        """Movie detail page should return HTTP 200."""
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertEqual(response.status_code, 200)

    def test_movie_detail_uses_correct_template(self):
        """Movie detail page should render movie_detail.html."""
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertTemplateUsed(response, "movie_detail.html")

    def test_movie_detail_formats_runtime_correctly(self):
        """Runtime of 139 mins should be formatted as 2h 19m."""
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertEqual(response.context["movie"]["formatted_runtime"], "2h 19m")

    def test_movie_detail_handles_missing_runtime(self):
        """Movie with no runtime should show N/A."""
        movie_no_runtime = MOCK_MOVIE.copy()
        movie_no_runtime["runtime"] = None
        self.mock_fetch.return_value = movie_no_runtime
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertEqual(response.context["movie"]["formatted_runtime"], "N/A")

    def test_movie_detail_passes_cast_to_context(self):
        """Movie detail page should pass cast to context."""
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertIn("cast", response.context)
        self.assertEqual(len(response.context["cast"]), 2)

    def test_movie_detail_passes_director_to_context(self):
        """Movie detail page should pass director to context."""
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertIn("director", response.context)
        self.assertEqual(response.context["director"]["name"], "David Fincher")

    def test_movie_detail_handles_empty_api_response(self):
        """Movie detail page should handle empty dict from API without crashing."""
        self.mock_fetch.return_value = {}
        self.mock_cast.return_value = []
        self.mock_director.return_value = None
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["movie"]["formatted_runtime"], "N/A")

    def test_movie_detail_accessible_without_login(self):
        """Movie detail page should be publicly accessible."""
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertEqual(response.status_code, 200)


