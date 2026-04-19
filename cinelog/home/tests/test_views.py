"""Tests for Cinelog home app views."""
from unittest.mock import patch, MagicMock
import requests as req_module
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase, Client
from django.urls import reverse, resolve
from home import views
from home.services import supabase
from home.services.tmdb import get_watch_providers
from django.http import HttpRequest

User = get_user_model()
supabase = supabase.get_supabase_client()


class SignupTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("signup")
        self.data = {
            "email": "user1@email.com",
            "username": "user1",
            "password1": "Test.1234!!",
            "password2": "Test.1234!!",
        }

    def test_signup_view_valid(self):
        """
        Test that the signup page loads.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signup.html")
        self.assertIn("form", response.context)

    @patch("home.views.supabase.supabase_sign_up", return_value=False)
    def test_invalid_email(self, mock_sign_up):
        """
        Test that a user cannot sign up if they have an invalid email.
        """
        data = {
            "email": "user1",
            "username": "user1",
            "password1": "Test.1234!!",
            "password2": "Test.1234!!",
        }
        response = self.client.post(self.url, data)
        mock_sign_up.assert_not_called()
        self.assertRedirects(response, reverse("signup"))

    @patch("home.views.supabase.supabase_sign_up")
    @patch("home.views.supabase.supabase_client.auth.get_user")
    @patch("home.views.UserCreationForm.is_valid", return_value=True)
    def test_signup_view_successful(self, mock_form_valid, mock_get_user, mock_sign_up):
        """
        Test post request when information is valid and user can sign up.
        """
        mock_get_user.return_value = {
            "user": {
                "id": "11111111-1111-1111-1111-111111111111",
            },
            "user_metadata": {"username": self.data["username"]},
            "email": self.data["email"],
        }
        response = self.client.post(self.url, self.data)
        mock_sign_up.assert_called_once()
        self.assertRedirects(response, reverse("movies"))

        # Ensure user is also signed in.
        session = self.client.session
        session.save()

        request = response.wsgi_request
        request.session["access_token"] = "ABCD123"
        request.session["supabase_username"] = self.data["username"]
        self.assertTrue(views.supabase.is_authenticated(request))

    @patch("home.views.supabase.supabase_sign_up")
    def test_signup_with_existing_username(self, mock_sign_up):
        """
        Test that user cannot sign up if username is same as another user or already have an account.
        """
        # Create user with same username.
        same_data = {
            "username": self.data["username"],
            "email": "helloworld@email.com",
            "password1": "password.5678",
            "password2": "password.5678",
        }
        mock_sign_up.return_value = False

        # Create user with same username if one does not already exist.
        response = self.client.post(self.url, same_data)
        self.assertRedirects(response, reverse("signup"))
        mock_sign_up.assert_called_once()

    def test_signup_different_passwords(self):
        """
        Test that user cannot sign up if their passwords do not match.
        """
        not_matching_data = {
            "email": "user123@email.com",
            "username": "user123",
            "password1": "Test.1234!!",
            "password2": "Test",
        }

        response = self.client.post(self.url, data=not_matching_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("signup"))

    def test_signup_blank_username(self):
        """
        Test that user cannot sign up if they do not provide a username.
        """
        no_username_data = {
            "email": "user123@email.com",
            "username": "",
            "password1": "Test.1234!!",
            "password2": "Test.1234!!",
        }

        response = self.client.post(self.url, data=no_username_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    @patch("home.views.supabase.supabase_sign_up", return_value=False)
    def test_signup_blank_email(self, mock_sign_up):
        """
        Test that user cannot sign up if they do not provide a username.
        """
        no_username_data = {
            "email": "",
            "username": "user123",
            "password1": "Test.1234!!",
            "password2": "Test.1234!!",
        }

        response = self.client.post(self.url, data=no_username_data)
        mock_sign_up.assert_not_called()
        self.assertRedirects(response, reverse("signup"))

    def test_signup_weak_password(self):
        """
        Test that user cannot sign up if they provide a weak password.
        """
        no_username_data = {
            "email": "user12345@email.com",
            "username": "user12345",
            "password1": "hello",
            "password2": "hello",
        }

        response = self.client.post(reverse("signup"), data=no_username_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())


class LoginTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("login")
        self.data = {"email": "user1@email.com", "password": "Test.1234!!"}

    def test_log_in_view_valid(self):
        """
        Test that the login page loads.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")

    @patch("home.views.supabase.supabase_log_in", return_value=True)
    def test_log_in_successful(self, mock_log_in):
        """
        Test that user with an account can login.
        """
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse("movies"))
        mock_log_in.assert_called_once()

    @patch("home.views.supabase.supabase_log_in", return_value=False)
    def test_log_in_failure_without_account(self, mock_log_in):
        """
        Test that user without an account cannot login.
        """
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")
        mock_log_in.assert_called_once()

    @patch("home.views.supabase.supabase_log_in", return_value=False)
    def test_log_in_with_invalid_email(self, mock_log_in):
        """
        Test that a user cannot sign up if they have an invalid email.
        """
        data = {"email": "user1", "password": "Test.1234!!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed("login.html")
        mock_log_in.assert_not_called()

    @patch("home.views.supabase.supabase_log_in", return_value=False)
    def test_log_in_with_empty_fields(self, mock_log_in):
        """
        Test that a user cannot sign up if they have an invalid email.
        """
        data = {"email": "", "password": ""}
        response = self.client.post(self.url, data)
        self.assertTemplateUsed("login.html")
        self.assertRedirects(response, reverse("login"))
        mock_log_in.assert_not_called()

    @patch("home.views.supabase.supabase_log_in", return_value=False)
    def test_log_in_with_no_email(self, mock_log_in):
        """
        Test that a user cannot sign up if they have an invalid email.
        """
        data = {"email": "", "password": "Test1234!!"}
        response = self.client.post(self.url, data)
        self.assertTemplateUsed("login.html")
        self.assertRedirects(response, reverse("login"))
        mock_log_in.assert_not_called()


class MagicLogin(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("magic_login")
        self.data = {"email": "user1@email.com"}

    def test_magic_login_view_valid(self):
        """
        Test that the login page loads.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "magic_link_login.html")

    @patch("home.views.supabase.send_magic_link_login")
    @patch("home.views.supabase.reached_limit_magic_login", return_value=False)
    def test_magic_login_successful(self, mock_reached_limit, mock_send_magic_link):
        """
        Test that link can be sent.
        """
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse("magic_login"))
        mock_send_magic_link.assert_called_once()

    @patch("home.views.supabase.send_magic_link_login")
    @patch("home.views.supabase.reached_limit_magic_login", return_value=False)
    def test_magic_failed_no_email_entered(
        self, mock_reached_limit, mock_send_magic_link
    ):
        """
        Test that no link sent if no email is entered.
        """
        data = {"email": ""}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("magic_login"))

    @patch("home.views.supabase.reached_limit_magic_login", return_value=True)
    def test_magic_failed_reached_limit_of_links(self, mock_reached_limit):
        """
        Test that no link is sent if user reaches limit of sending links.
        """
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse("magic_login"))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                "Reached max limit of magic logins for the hour. Try later or login with password."
            )
            in str(m)
            for m in messages
        )


class MagicCallback(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("callback")

    @patch("home.views.supabase.get_user_magic_link", return_value=True)
    def test_magic_callback_sucessful(self, mock_get_magic_link):
        """
        Test that user is successfully redirected to account with link.
        """
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("movies"))
        mock_get_magic_link.assert_called_once()

    @patch("home.views.supabase.get_user_magic_link", return_value=False)
    def test_magic_callback_fail(self, mock_get_magic_link):
        """
        Test that if link fails, user is redirected to magic_login page.
        """
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("magic_login"))
        mock_get_magic_link.assert_called_once()


class Logout(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("logout")

    @patch("home.views.supabase.logout")
    def test_logout(self, mock_logout):
        """
        Test that a user is logged out and redirected to home page.
        """
        response = self.client.get(self.url)
        mock_logout.assert_called_once()
        self.assertRedirects(response, "/")


class LandingPageViewTest(TestCase):
    """Tests for the landing page view."""

    def setUp(self):
        self.client = Client()

    def test_landing_page_returns_200(self):
        """Landing page should return HTTP 200."""
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)

    def test_landing_page_uses_correct_template(self):
        """Landing page should render landing.html."""
        response = self.client.get(reverse("landing"))
        self.assertTemplateUsed(response, "landing.html")

    def test_landing_page_accessible_without_login(self):
        """Landing page should be publicly accessible."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class AuthenticationTest(TestCase):
    """Tests for user authentication flows."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123", email="test@example.com"
        )

    def test_login_page_loads_successfully(self):
        """Login page should load with HTTP 200."""
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")

    def test_user_creation(self):
        """User objects should be created correctly."""
        self.assertEqual(self.user.username, "testuser")
        self.assertTrue(self.user.check_password("testpassword123"))

    def test_logout_redirects_authenticated_user(self):
        """Authenticated user logout should succeed (200 or 302 depending on config)."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.post("/logout/")
        self.assertIn(response.status_code, [200, 302])


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
            {
                "name": "Brad Pitt",
                "character": "Tyler Durden",
                "profile_path": "/abc.jpg",
            },
            {
                "name": "Edward Norton",
                "character": "The Narrator",
                "profile_path": "/xyz.jpg",
            },
        ],
        "crew": [
            {"name": "David Fincher", "job": "Director", "profile_path": "/dir.jpg"},
        ],
    },
}

MOCK_MOVIES_LIST = [MOCK_MOVIE]


class MoviesViewTest(TestCase):
    """Tests for the movies listing page."""

    def setUp(self):
        self.client = Client()
        # patch once for all tests in this class
        self.mock_fetch = patch(
            "home.views.fetch_movies", return_value=MOCK_MOVIES_LIST
        ).start()
        self.addCleanup(
            patch.stopall
        )  # stops all patches after each test automatically

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
        self.mock_fetch = patch(
            "home.views.fetch_movie_detail", return_value=MOCK_MOVIE.copy()
        ).start()
        self.mock_cast = patch(
            "home.views.get_cast", return_value=MOCK_MOVIE["credits"]["cast"]
        ).start()
        self.mock_director = patch(
            "home.views.get_director", return_value=MOCK_MOVIE["credits"]["crew"][0]
        ).start()
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
        self.mock_fetch.return_value = {"id": 550, "formatted_runtime": "N/A"}
        self.mock_cast.return_value = []
        self.mock_director.return_value = None
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["movie"]["formatted_runtime"], "N/A")

    def test_movie_detail_accessible_without_login(self):
        """Movie detail page should be publicly accessible."""
        response = self.client.get(reverse("movie_detail", args=[550]))
        self.assertEqual(response.status_code, 200)


class WatchlistTest(TestCase):
    VALID_USER_ID = "11111111-1111-1111-1111-111111111111"

    def setUp(self):
        self.client = Client()
        self.movie_id = 550
        self.movie_list = [
            {"id": 1, "title": "Avengers"},
            {"id": 2, "title": "Black Panther"},
            {"id": 3, "title": "Hoppers"},
        ]
        self.movie_ids = [1, 2, 3]
        self.add_url = reverse("add_to_watchlist", args=[self.movie_id])
        self.remove_url = reverse("remove_from_watchlist", args=[self.movie_id])
        self.watchlist_url = reverse("watchlist")
        self.movie_url = reverse("movie_detail", args=[self.movie_id])
        self.user_id = "11111111-1111-1111-1111-111111111111"

    @patch("home.views.supabase.get_user_id", return_value=VALID_USER_ID)
    @patch(
        "home.views.supabase.insert_in_watchlist",
        return_value=(True, "Added successfully"),
    )
    def test_add_to_watchlist_success(self, mock_insert, mock_user_id):
        """Test adding a movie is inserted successfully."""
        response = self.client.post(self.add_url)
        mock_insert.assert_called_once_with(self.user_id, self.movie_id)
        self.assertRedirects(response, self.movie_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Added successfully" in str(m) for m in messages))

    @patch("home.views.supabase.get_user_id", return_value=VALID_USER_ID)
    @patch(
        "home.views.supabase.insert_in_watchlist",
        return_value=(False, "Error: Movie is already in watchlist."),
    )
    @patch("home.services.supabase.get_supabase_client", return_value=MagicMock())
    def test_add_to_watchlist_not_success(self, mock_client, mock_insert, mock_user_id):
        """
        Test adding a movie is inserted unsccessfully.
        """
        response = self.client.post(self.add_url)
        mock_insert.assert_called_once_with(self.user_id, self.movie_id)
        self.assertRedirects(response, self.movie_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Error:" in str(m) for m in messages))

    @patch("home.views.supabase.get_user_id", return_value=None)
    def test_add_to_watchlist_not_logged_in(self, mock_user_id):
        """
        Test a movie cannot be added if user is not logged in.
        """
        response = self.client.post(self.add_url)
        self.assertRedirects(response, reverse("login"))

    @patch("home.views.supabase.get_user_id", return_value=VALID_USER_ID)
    @patch("home.views.supabase.delete_in_watchlist", return_value=False)
    def test_remove_from_watchlist_not_success(self, mock_delete, mock_user_id):
        """Test that error is shown if there is an error."""
        response = self.client.post(self.remove_url, HTTP_REFERER="/watchlist/")
        mock_delete.assert_called_once_with(self.user_id, self.movie_id)
        self.assertRedirects(response, "/watchlist/")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Unable to remove movie. Please try again." in str(m) for m in messages)
        )

    @patch("home.views.supabase.get_user_id", return_value=None)
    def test_remove_from_watchlist_not_logged_in(self, mock_user_id):
        """Test that a user cannot remove if they are not logged in."""
        response = self.client.post(self.remove_url)
        self.assertRedirects(response, reverse("login"))

    @patch("home.views.supabase.get_watchlist", return_value=[550])
    @patch("home.views.fetch_movies", return_value={"id": 550, "title": "Fight Club"})
    @patch("home.views.supabase.get_user_id", return_value=VALID_USER_ID)
    def test_watchlist_view_logged_in(
        self, mock_get_user, mock_fetch, mock_get_watchlist
    ):
        response = self.client.get(reverse("watchlist"))
        self.assertTemplateUsed(response, "watchlist.html")
        self.assertIn("movies", response.context)
        self.assertEqual(response.context["movies"][0]["title"], "Fight Club")

    @patch("home.views.supabase.get_user_id", return_value=None)
    def test_watchlist_view_not_logged_in(self, mock_user_id):
        """Test watchlist page if shown worrectly if user not logged in."""
        response = self.client.get(self.watchlist_url)
        self.assertTemplateUsed(response, "watchlist.html")
        self.assertNotIn("movies", response.context)

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_title_sort_ascending(
        self, mock_fetch, mock_get_watchlist, mock_get_user_id
    ):
        """
        Test that movies are sorted correctly in ascending order for title.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = self.movie_ids
        mock_fetch.side_effect = lambda movie_id, single: next(
            (m for m in self.movie_list if m["id"] == movie_id), {}
        )

        response = self.client.get("/watchlist/?sort=ascending_title")
        movies = response.context["movies"]
        titles = [m["title"] for m in movies]
        self.assertEqual(titles, ["Avengers", "Black Panther", "Hoppers"])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_title_sort_descending(
        self, mock_fetch, mock_get_watchlist, mock_get_user_id
    ):
        """
        Test that movies are sorted correctly in descending order for title.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = self.movie_ids
        mock_fetch.side_effect = lambda movie_id, single: next(
            (m for m in self.movie_list if m["id"] == movie_id), {}
        )

        response = self.client.get("/watchlist/?sort=descending_title")
        movies = response.context["movies"]
        titles = [m["title"] for m in movies]
        self.assertEqual(titles, ["Hoppers", "Black Panther", "Avengers"])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_date_sort_ascending(
        self, mock_fetch, mock_get_watchlist, mock_get_user_id
    ):
        """
        Test that movies are sorted correctly in ascending order for date.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = [2, 1, 3]
        mock_fetch.side_effect = lambda movie_id, single: next(
            (m for m in self.movie_list if m["id"] == movie_id), {}
        )

        response = self.client.get("/watchlist/?sort=ascending_date")
        movies = response.context["movies"]
        ids = [m["id"] for m in movies]
        self.assertEqual(ids, [2, 1, 3])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_date_sort_descending(
        self, mock_fetch, mock_get_watchlist, mock_get_user_id
    ):
        """
        Test that movies are sorted correctly in descending order for date.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = [3, 1, 2]  # IDs in descending date order
        mock_fetch.side_effect = lambda movie_id, single: next(
            (m for m in self.movie_list if m["id"] == movie_id), {}
        )

        response = self.client.get("/watchlist/?sort=descending_date")
        movies = response.context["movies"]
        ids = [m["id"] for m in movies]
        self.assertEqual(ids, [3, 1, 2])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_missing_movie(
        self, mock_fetch, mock_get_watchlist, mock_get_user_id
    ):
        """
        Test that movie ids that do not exist are not returned.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = [1, 2, 99]  # 99 does not exist
        mock_fetch.side_effect = lambda movie_id, single: next(
            (m for m in self.movie_list if m["id"] == movie_id), {}
        )

        response = self.client.get("/watchlist/")
        movies = response.context["movies"]
        ids = [m["id"] for m in movies]
        self.assertNotIn(99, ids)


class HiddenMoviesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.mock_user_id = "11111111-1111-1111-1111-111111111111"
        session = self.client.session
        session["supabase_user_id"] = self.mock_user_id
        session["access_token"] = "mock_token"
        session.save()

    @patch(
        "home.views.supabase.get_user_id",
        return_value="11111111-1111-1111-1111-111111111111",
    )
    @patch(
        "home.views.supabase.insert_hidden_movie",
        return_value=(True, "Movie hidden successfully."),
    )
    def test_hide_movie_success(self, mock_insert, mock_get_user):
        """Test that a logged-in user can hide a movie."""
        response = self.client.post(reverse("hide_movie", args=[278]))
        mock_insert.assert_called_once_with("11111111-1111-1111-1111-111111111111", 278)
        self.assertRedirects(response, reverse("movie_detail", args=[278]))

    @patch("home.views.supabase.get_user_id", return_value=None)
    def test_hide_movie_requires_login(self, mock_get_user):
        """Test that an unauthenticated user is redirected to login when trying to hide."""
        response = self.client.post(reverse("hide_movie", args=[278]))
        self.assertRedirects(response, reverse("login"))

    @patch("home.views.supabase.delete_hidden_movie", return_value=True)
    @patch(
        "home.views.supabase.get_user_id",
        return_value="11111111-1111-1111-1111-111111111111",
    )
    def test_unhide_movie_success(self, mock_get_user, mock_delete):
        """Test that a logged-in user can unhide a movie."""
        response = self.client.post(reverse("unhide_movie", args=[278]))
        self.assertEqual(response.status_code, 302)
        mock_delete.assert_called_once_with("11111111-1111-1111-1111-111111111111", 278)

    @patch("home.views.supabase.get_user_id", return_value=None)
    def test_unhide_movie_requires_login(self, mock_get_user):
        """Test that an unauthenticated user is redirected to login when trying to unhide."""
        response = self.client.post(reverse("unhide_movie", args=[278]))
        self.assertRedirects(response, reverse("login"))

    @patch("home.views.supabase.get_hidden_movies", return_value=[278, 155])
    @patch(
        "home.views.fetch_movies",
        side_effect=lambda mid, single=False: {
            "id": mid,
            "title": f"Movie {mid}",
            "poster_path": "",
            "vote_average": 8.0,
        },
    )
    @patch(
        "home.views.supabase.get_user_id",
        return_value="11111111-1111-1111-1111-111111111111",
    )
    def test_hidden_movies_page_renders(
        self, mock_get_user, mock_fetch, mock_get_hidden
    ):
        """Test that the hidden movies page loads and shows hidden movies."""
        response = self.client.get(reverse("account"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account.html")
        self.assertEqual(len(response.context["movies"]), 2)

    @patch("home.views.supabase.get_hidden_movies", return_value=[])
    @patch(
        "home.views.supabase.get_user_id",
        return_value="11111111-1111-1111-1111-111111111111",
    )
    def test_hidden_movies_page_empty(self, mock_get_user, mock_get_hidden):
        """Test that the hidden movies page renders with no movies."""
        response = self.client.get(reverse("account"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["movies"]), 0)

    @patch("home.views.supabase.get_hidden_movies", return_value=[278])
    @patch(
        "home.views.fetch_movies",
        side_effect=lambda category: (
            [{"id": 278, "title": "Shawshank", "vote_average": 8.7, "poster_path": ""}]
            if category == "popular"
            else []
        ),
    )
    @patch(
        "home.views.supabase.get_user_id",
        return_value="11111111-1111-1111-1111-111111111111",
    )
    def test_hidden_movie_filtered_from_movies_view(
        self, mock_get_user, mock_fetch, mock_get_hidden
    ):
        """Test that hidden movies do not appear on the main movies page."""
        response = self.client.get(reverse("movies"))
        self.assertEqual(response.status_code, 200)
        movies = response.context["movies"]
        ids = [m["id"] for m in movies]
        self.assertNotIn(278, ids)

        # ==================== SEARCH FUNCTIONALITY TESTS ====================


class SearchMoviesViewTest(TestCase):
    """Tests for the movie search functionality."""

    def setUp(self):
        self.client = Client()
        self.search_url = reverse("search_movies")
        self.mock_search_results = [
            {
                "id": 550,
                "title": "Fight Club",
                "vote_average": 8.8,
                "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
                "release_date": "1999-10-15",
            },
            {
                "id": 680,
                "title": "Pulp Fiction",
                "vote_average": 8.9,
                "poster_path": "/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg",
                "release_date": "1994-10-14",
            },
        ]

        # Patch the search_movies function for all tests in this class
        self.mock_search = patch("home.views.search_movies").start()
        self.addCleanup(patch.stopall)

    def test_search_page_returns_200(self):
        """Search page should return HTTP 200."""
        response = self.client.get(self.search_url)
        self.assertEqual(response.status_code, 200)

    def test_search_page_uses_correct_template(self):
        """Search page should render search_results.html."""
        response = self.client.get(self.search_url)
        self.assertTemplateUsed(response, "search_results.html")

    def test_search_page_accessible_without_login(self):
        """Search page should be publicly accessible."""
        response = self.client.get(self.search_url)
        self.assertEqual(response.status_code, 200)

    def test_search_with_valid_query_returns_results(self):
        """Search with valid query should return movie results."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "fight club"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("movies", response.context)
        self.assertEqual(len(response.context["movies"]), 2)
        self.assertEqual(response.context["search_query"], "fight club")
        self.assertTrue(response.context["is_search"])

    def test_search_displays_movie_titles(self):
        """Search results should display movie titles."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "fight"})

        self.assertContains(response, "Fight Club")
        self.assertContains(response, "Pulp Fiction")

    def test_search_with_empty_query_returns_no_results(self):
        """Search with empty query should show empty results."""
        response = self.client.get(self.search_url, {"q": ""})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["movies"], [])
        self.assertEqual(response.context["search_query"], "")
        self.mock_search.assert_not_called()

    def test_search_with_no_query_parameter(self):
        """Search with no query parameter should show search form."""
        response = self.client.get(self.search_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["movies"], [])
        self.mock_search.assert_not_called()

    def test_search_with_no_results(self):
        """Search with no matching results should show no results message."""
        self.mock_search.return_value = []

        response = self.client.get(self.search_url, {"q": "nonexistentmoviexyz"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["movies"]), 0)
        self.assertContains(response, "No movies found")

    def test_search_preserves_query_in_input_field(self):
        """Search input field should preserve the query after search."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "inception"})

        self.assertContains(response, 'value="inception"')

    def test_search_shows_result_count(self):
        """Search should display the number of results found."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "fight"})

        self.assertContains(response, "Showing 2 results for")

    def test_search_shows_singular_result_count(self):
        """Search with one result should show singular 'result' not 'results'."""
        self.mock_search.return_value = [self.mock_search_results[0]]

        response = self.client.get(self.search_url, {"q": "fight club"})

        self.assertContains(response, "Showing 1 result for")

    def test_search_handles_special_characters(self):
        """Search should handle special characters in query."""
        self.mock_search.return_value = []

        special_queries = [
            "!@#$%",
            "star wars: episode v",
            "terminator 2: judgment day",
        ]
        for query in special_queries:
            response = self.client.get(self.search_url, {"q": query})
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "Error")

    def test_search_handles_long_query(self):
        """Search should handle long query strings."""
        self.mock_search.return_value = []
        long_query = "a" * 200

        response = self.client.get(self.search_url, {"q": long_query})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["search_query"], long_query)

    def test_search_handles_unicode_characters(self):
        """Search should handle unicode/foreign characters."""
        self.mock_search.return_value = []

        unicode_queries = ["café", "日本", "élève", "München"]
        for query in unicode_queries:
            response = self.client.get(self.search_url, {"q": query})
            self.assertEqual(response.status_code, 200)

    def test_search_links_to_movie_detail(self):
        """Search results should link to correct movie detail pages."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "fight"})

        self.assertContains(response, f"/movies/{self.mock_search_results[0]['id']}/")
        self.assertContains(response, f"/movies/{self.mock_search_results[1]['id']}/")

    def test_search_displays_movie_posters(self):
        """Search results should display movie poster images."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "fight"})

        self.assertContains(response, "https://image.tmdb.org/t/p/w200")
        self.assertContains(response, self.mock_search_results[0]["poster_path"])

    def test_search_displays_ratings(self):
        """Search results should display movie ratings."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "fight"})

        self.assertContains(response, "★ 8.8")
        self.assertContains(response, "★ 8.9")

    def test_search_displays_release_years(self):
        """Search results should display release years."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "fight"})

        self.assertContains(response, "1999")
        self.assertContains(response, "1994")

    def test_search_with_whitespace_query(self):
        """Search should trim whitespace from query."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "  fight club  "})

        self.mock_search.assert_called_with("fight club")
        self.assertEqual(response.context["search_query"], "fight club")

    def test_search_case_insensitivity_display(self):
        """Search display should preserve original case but work case-insensitively."""
        self.mock_search.return_value = self.mock_search_results

        response = self.client.get(self.search_url, {"q": "FIGHT CLUB"})

        # Query should be preserved as entered for display
        self.assertEqual(response.context["search_query"], "FIGHT CLUB")
        # But the search function should be called with the query (implementation handles case)
        self.mock_search.assert_called_with("FIGHT CLUB")


class SearchAPIIntegrationTest(TestCase):
    """Tests for search_movies service function (mocked API calls)."""

    def setUp(self):
        self.mock_movie_data = {
            "results": [
                {
                    "id": 550,
                    "title": "Fight Club",
                    "vote_average": 8.8,
                    "poster_path": "/poster.jpg",
                    "release_date": "1999-10-15",
                }
            ]
        }

    @patch("home.services.tmdb.requests.get")
    def test_search_movies_successful_api_call(self, mock_get):
        """Test search_movies successfully calls TMDB API."""
        from home.services.tmdb import search_movies

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_movie_data
        mock_get.return_value = mock_response

        results = search_movies("fight club")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Fight Club")
        mock_get.assert_called_once()

        # Verify correct API endpoint was called
        args, kwargs = mock_get.call_args
        self.assertIn("/search/movie", args[0])
        self.assertEqual(kwargs["params"]["query"], "fight club")

    @patch("home.services.tmdb.requests.get")
    def test_search_movies_empty_results(self, mock_get):
        """Test search_movies handles empty results from API."""
        from home.services.tmdb import search_movies

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        results = search_movies("nonexistentmovie")

        self.assertEqual(results, [])


class SearchURLTests(TestCase):
    """Tests for search URL routing."""

    def test_search_url_resolves_correctly(self):
        """Test that search URL resolves to correct view."""
        resolver = resolve("/movies/search/")
        self.assertEqual(resolver.view_name, "search_movies")

    def test_search_url_accepts_query_parameter(self):
        """Test that search URL accepts and processes query parameter."""
        response = self.client.get("/movies/search/", {"q": "test"})
        self.assertEqual(response.status_code, 200)

    def test_search_without_trailing_slash(self):
        """Test search URL without trailing slash redirects."""
        response = self.client.get("/movies/search")
        self.assertEqual(response.status_code, 301)  # Permanent redirect


class SearchTemplateContentTests(TestCase):
    """Tests for search template content and structure."""

    def setUp(self):
        self.client = Client()
        self.search_url = reverse("search_movies")

    @patch("home.views.search_movies")
    def test_template_contains_search_form(self, mock_search):
        """Test that template includes search form."""
        mock_search.return_value = []

        response = self.client.get(self.search_url)

        self.assertContains(response, "<form")
        self.assertContains(response, 'method="GET"')
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'placeholder="Search for any movie by title"')

    @patch("home.views.search_movies")
    def test_template_contains_search_button(self, mock_search):
        """Test that template includes search button."""
        mock_search.return_value = []

        response = self.client.get(self.search_url)

        self.assertContains(response, 'button type="submit"')
        self.assertContains(response, "Search")

    @patch("home.views.search_movies")
    def test_template_shows_example_queries_when_no_search(self, mock_search):
        """Test template shows example queries on initial load."""
        mock_search.return_value = []

        response = self.client.get(self.search_url)

        self.assertContains(response, "Examples:")
        self.assertContains(response, '"Inception"')
        self.assertContains(response, '"The Matrix"')
        self.assertContains(response, '"Toy Story"')

    @patch("home.views.search_movies")
    def test_template_does_not_show_examples_after_search(self, mock_search):
        """Test template does not show examples after a search is performed."""
        mock_search.return_value = [{"id": 1, "title": "Test"}]

        response = self.client.get(self.search_url, {"q": "test"})

        self.assertNotContains(response, "Examples:")
        self.assertContains(response, "Showing")

    @patch("home.views.search_movies")
    def test_template_uses_grid_layout(self, mock_search):
        """Test template uses CSS Grid for results layout."""
        mock_search.return_value = [{"id": 1, "title": "Test"}]

        response = self.client.get(self.search_url, {"q": "test"})

        self.assertContains(response, "movie-grid")
        self.assertContains(response, "grid-template-columns")

    @patch("home.views.search_movies")
    def test_template_shows_clear_search_option(self, mock_search):
        """Test template provides way to clear search and see all movies."""
        mock_search.return_value = []

        response = self.client.get(self.search_url, {"q": "test"})

        # Should have link back to movies page or clear search
        self.assertContains(response, 'href="/movies/"')


class AccountViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("account")
        self.user_id = "11111111-1111-1111-1111-111111111111"

    @patch("home.views.supabase.get_user_id", return_value=None)
    def test_account_redirects_when_not_logged_in(self, mock_user):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "movies.html")

    @patch("home.views.supabase.get_user_id", return_value="user123")
    @patch("home.views.supabase.get_hidden_movies", return_value=[])
    @patch("home.views.user_statistics")
    @patch("home.views.render")
    def test_account_view_no_hidden_movies(
        self, mock_render, mock_stats, mock_hidden, mock_user_id
    ):
        """
        Test if user has no hidden movies.
        """
        request = HttpRequest()

        mock_stats.get_genre_statistics.return_value = ("Action", {})
        mock_stats.get_size_of_watchlist.return_value = 1
        mock_stats.get_size_of_library.return_value = 2
        mock_stats.get_num_hours_in_library.return_value = 10
        mock_stats.get_average_rating.return_value = 4.5
        mock_stats.get_monthly_logged_movies.return_value = []
        mock_stats.get_library_months_for_year.return_value = [1, 2, 3]
        mock_stats.get_logged_monthly_average.return_value = 2
        mock_stats.get_days_logged.return_value = 5
        mock_stats.get_top_five_movies.return_value = []

        views.account_view(request)

        args, kwargs = mock_render.call_args
        context = args[2]

        assert context["movies"] == []
        assert context["top_genre"] == "Action"

    @patch("home.views.supabase.get_user_id", return_value="user123")
    @patch("home.views.supabase.get_hidden_movies", return_value=["1", "2", "3"])
    @patch("home.views.fetch_movies")
    @patch("home.views.user_statistics")
    @patch("home.views.render")
    def test_account_view_filters_invalid_movies(
        self, mock_render, mock_stats, mock_fetch, mock_hidden, mock_user_id
    ):
        """
        Test correct results if given movies missing id or have none for id.
        """
        request = HttpRequest()

        mock_fetch.side_effect = [{"id": "1", "title": "Valid Movie"}, {}, {"id": None}]

        mock_stats.get_genre_statistics.return_value = ("Drama", {})
        views.account_view(request)
        args, kwargs = mock_render.call_args
        context = args[2]

        assert len(context["movies"]) == 1
        assert context["movies"][0]["id"] == "1"

    @patch("home.views.supabase.get_user_id", return_value="user123")
    @patch("home.views.supabase.get_hidden_movies", return_value=[])
    @patch("home.views.user_statistics")
    @patch("home.views.render")
    def test_account_view_hidden_movies_none(
        self, mock_render, mock_stats, mock_hidden, mock_user_id
    ):
        """
        Test if there are no hidden movies.
        """
        request = HttpRequest()
        mock_stats.get_genre_statistics.return_value = ("Comedy", {})

        views.account_view(request)
        args, kwargs = mock_render.call_args
        context = args[2]

        assert context["movies"] == []


class WhereToWatchTest(TestCase):
    """Tests for the where_to_watch_view endpoint."""

    def setUp(self):
        """Set up test client and movie ID."""
        self.client = Client()
        self.movie_id = 550

    @patch("home.views.get_watch_providers")
    def test_where_to_watch_returns_200(self, mock_providers):
        """Where to watch endpoint should return HTTP 200."""
        mock_providers.return_value = {
            "streaming": [{"provider_name": "Netflix", "logo_path": "/abc.jpg"}],
            "rent": [], "buy": [],
            "link": "https://www.themoviedb.org/movie/550/watch",
        }
        response = self.client.get(reverse("where_to_watch", args=[self.movie_id]))
        self.assertEqual(response.status_code, 200)

    @patch("home.views.get_watch_providers")
    def test_where_to_watch_returns_json(self, mock_providers):
        """Where to watch endpoint should return application/json content type."""
        mock_providers.return_value = {"streaming": [], "rent": [], "buy": [], "link": ""}
        response = self.client.get(reverse("where_to_watch", args=[self.movie_id]))
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertIn("streaming", data)
        self.assertIn("rent", data)
        self.assertIn("buy", data)

    @patch("home.views.get_watch_providers")
    def test_where_to_watch_returns_providers(self, mock_providers):
        """Where to watch endpoint should return provider data in response."""
        mock_providers.return_value = {
            "streaming": [{"provider_name": "Netflix", "logo_path": "/n.jpg"}],
            "rent": [{"provider_name": "Apple TV", "logo_path": "/a.jpg"}],
            "buy": [],
            "link": "https://www.themoviedb.org/movie/550/watch",
        }
        response = self.client.get(reverse("where_to_watch", args=[self.movie_id]))
        data = response.json()
        self.assertEqual(len(data["streaming"]), 1)
        self.assertEqual(data["streaming"][0]["provider_name"], "Netflix")

    @patch("home.views.get_watch_providers")
    def test_where_to_watch_empty_when_unavailable(self, mock_providers):
        """Where to watch endpoint should handle empty provider response gracefully."""
        mock_providers.return_value = {}
        response = self.client.get(reverse("where_to_watch", args=[self.movie_id]))
        self.assertEqual(response.status_code, 200)


class WatchProvidersServiceTest(TestCase):
    """Tests for the get_watch_providers TMDB service function."""

    @patch("home.services.tmdb.requests.get")
    def test_get_watch_providers_success(self, mock_get):
        """get_watch_providers should return parsed provider lists on success."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": {
                "US": {
                    "flatrate": [{"provider_name": "Netflix", "logo_path": "/n.jpg"}],
                    "rent": [], "buy": [],
                    "link": "https://example.com",
                }
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        result = get_watch_providers(550)
        self.assertEqual(len(result["streaming"]), 1)
        self.assertEqual(result["streaming"][0]["provider_name"], "Netflix")

    @patch("home.services.tmdb.requests.get")
    def test_get_watch_providers_request_failure(self, mock_get):
        """get_watch_providers should return empty dict on request failure."""
        mock_get.side_effect = req_module.RequestException("Network error")
        result = get_watch_providers(550)
        self.assertEqual(result, {})

    @patch("home.services.tmdb.requests.get")
    def test_get_watch_providers_missing_country(self, mock_get):
        """get_watch_providers should return empty lists when country code not in results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        result = get_watch_providers(550)
        self.assertEqual(result["streaming"], [])
        self.assertEqual(result["rent"], [])
        self.assertEqual(result["buy"], [])
