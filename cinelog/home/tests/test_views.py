from django.test import TestCase, Client
from django.urls import reverse, resolve
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from home.services import supabase
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from home import views

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
            "password2": "Test.1234!!"
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
            "password2": "Test.1234!!"
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
            "email": self.data["email"]
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
            "password2": "password.5678"
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
        self.data = {
            "email": "user1@email.com",
            "password": "Test.1234!!"
        }

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
        data = {
            "email": "user1",
            "password": "Test.1234!!"
        }
        response = self.client.post(self.url, data)
        self.assertTemplateUsed("login.html")
        mock_log_in.assert_not_called()

    @patch("home.views.supabase.supabase_log_in", return_value=False)
    def test_log_in_with_empty_fields(self, mock_log_in):
        """
        Test that a user cannot sign up if they have an invalid email.
        """
        data = {
            "email": "",
            "password": ""
        }
        response = self.client.post(self.url, data)
        self.assertTemplateUsed("login.html")
        self.assertRedirects(response, reverse("login"))
        mock_log_in.assert_not_called()

    @patch("home.views.supabase.supabase_log_in", return_value=False)
    def test_log_in_with_no_email(self, mock_log_in):
        """
        Test that a user cannot sign up if they have an invalid email.
        """
        data = {
            "email": "",
            "password": "Test1234!!"
        }
        response = self.client.post(self.url, data)
        self.assertTemplateUsed("login.html")
        self.assertRedirects(response, reverse("login"))
        mock_log_in.assert_not_called()


class MagicLogin(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("magic_login")
        self.data = {
            "email": "user1@email.com"
        }
    

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
    def test_magic_failed_no_email_entered(self, mock_reached_limit, mock_send_magic_link):
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
            any
            ("Reached max limit of magic logins for the hour. Try later or login with password.") 
            in str(m) for m in messages)

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


    def test_login_page_loads_successfully(self):
        """Login page should load with HTTP 200."""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_user_creation(self):
        """User objects should be created correctly."""
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.check_password('testpassword123'))

    def test_logout_redirects_authenticated_user(self):
        """Authenticated user logout should succeed (200 or 302 depending on config)."""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post('/logout/')
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
        self.user_id = "1111111-1111111"

    @patch("home.views.supabase.get_user_id", return_value="user123")
    @patch("home.views.supabase.insert_in_watchlist", return_value=(True, "Added successfully"))
    def test_add_to_watchlist_success(self, mock_insert, mock_user_id):
        """Test adding a movie is inserted successfully."""
        response = self.client.post(self.add_url)
        mock_insert.assert_called_once_with("user123", self.movie_id)
        self.assertRedirects(response, self.movie_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Added successfully" in str(m) for m in messages))

    @patch("home.views.supabase.get_user_id", return_value="user123")
    @patch("home.views.supabase.insert_in_watchlist", return_value=(False, "Error: Movie is already in watchlist."))
    @patch("home.services.supabase.get_supabase_client", return_value=MagicMock())
    def test_add_to_watchlist_not_success(self, mock_client, mock_insert, mock_user_id):
        """
        Test adding a movie is inserted unsccessfully.
        """
        response = self.client.post(self.add_url)
        mock_insert.assert_called_once_with("user123", self.movie_id)
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

    @patch("home.views.supabase.get_user_id", return_value="user123")
    @patch("home.views.supabase.delete_in_watchlist", return_value=False)
    def test_remove_from_watchlist_not_success(self, mock_delete, mock_user_id):
        """Test that error is shown if there is an error."""
        response = self.client.post(self.remove_url, HTTP_REFERER="/watchlist/")
        mock_delete.assert_called_once_with("user123", self.movie_id)
        self.assertRedirects(response, "/watchlist/")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Unable to remove movie. Please try again." in str(m) for m in messages))


    @patch("home.views.supabase.get_user_id", return_value=None)
    def test_remove_from_watchlist_not_logged_in(self, mock_user_id):
        """Test that a user cannot remove if they are not logged in."""
        response = self.client.post(self.remove_url)
        self.assertRedirects(response, reverse("login"))

    @patch("home.views.supabase.get_user_id", return_value="user123")
    @patch("home.views.supabase.get_watchlist", return_value=[550])
    @patch("home.views.fetch_movies", return_value={"id": 550, "title": "Fight Club"})
    def test_watchlist_view_logged_in(self, mock_fetch, mock_get_watchlist, mock_user_id):
        """Test that the watchlist page is correctly displayed if used logged in."""
        response = self.client.get(self.watchlist_url)
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
    def test_watchlist_view_title_sort_ascending(self, mock_fetch, mock_get_watchlist, mock_get_user_id):
        """
        Test that movies are sorted correctly in ascending order for title.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = self.movie_ids
        mock_fetch.side_effect = lambda movie_id, single: next((m for m in self.movie_list if m["id"] == movie_id), {})

        response = self.client.get("/watchlist/?sort=ascending_title")
        movies = response.context["movies"]
        titles = [m["title"] for m in movies]
        self.assertEqual(titles, ["Avengers", "Black Panther", "Hoppers"])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_title_sort_descending(self, mock_fetch, mock_get_watchlist, mock_get_user_id):
        """
        Test that movies are sorted correctly in descending order for title.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = self.movie_ids
        mock_fetch.side_effect = lambda movie_id, single: next((m for m in self.movie_list if m["id"] == movie_id), {})

        response = self.client.get("/watchlist/?sort=descending_title")
        movies = response.context["movies"]
        titles = [m["title"] for m in movies]
        self.assertEqual(titles, ["Hoppers", "Black Panther", "Avengers"])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_date_sort_ascending(self, mock_fetch, mock_get_watchlist, mock_get_user_id):
        """
        Test that movies are sorted correctly in ascending order for date.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = [2, 1, 3] 
        mock_fetch.side_effect = lambda movie_id, single: next((m for m in self.movie_list if m["id"] == movie_id), {})

        response = self.client.get("/watchlist/?sort=ascending_date")
        movies = response.context["movies"]
        ids = [m["id"] for m in movies]
        self.assertEqual(ids, [2, 1, 3])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_date_sort_descending(self, mock_fetch, mock_get_watchlist, mock_get_user_id):
        """
        Test that movies are sorted correctly in descending order for date.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = [3, 1, 2]  # IDs in descending date order
        mock_fetch.side_effect = lambda movie_id, single: next((m for m in self.movie_list if m["id"] == movie_id), {})

        response = self.client.get("/watchlist/?sort=descending_date")
        movies = response.context["movies"]
        ids = [m["id"] for m in movies]
        self.assertEqual(ids, [3, 1, 2])

    @patch("home.views.supabase.get_user_id")
    @patch("home.views.supabase.get_watchlist")
    @patch("home.views.fetch_movies")
    def test_watchlist_view_missing_movie(self, mock_fetch, mock_get_watchlist, mock_get_user_id):
        """
        Test that movie ids that do not exist are not returned.
        """
        mock_get_user_id.return_value = self.user_id
        mock_get_watchlist.return_value = [1, 2, 99]  # 99 does not exist
        mock_fetch.side_effect = lambda movie_id, single: next((m for m in self.movie_list if m["id"] == movie_id), {})

        response = self.client.get("/watchlist/")
        movies = response.context["movies"]
        ids = [m["id"] for m in movies]
        self.assertNotIn(99, ids)