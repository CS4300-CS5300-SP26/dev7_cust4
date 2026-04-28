from unittest.mock import patch, MagicMock
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase, RequestFactory
from django.core.cache import cache
from django.contrib.messages import get_messages
from home.services import supabase

MOCK_SIGN_UP = {
    "user": {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_metadata": {"username": "user1234"},
        "aud": "authenticated",
        "email": "email@example.com",
    }
}

MOCK_GET_USER = {
    "user": {
        "id": "11111111-1111-1111-1111-111111111111",
        "app_metadata": {"provider": "email", "providers": []},
        "email": "email@example.com",
    }
}

MOCK_USERNAME = MOCK_SIGN_UP["user"]["user_metadata"]["username"]
MOCK_EMAIL = MOCK_SIGN_UP["user"]["email"]
MOCK_PASSWORD = "Test1234!!"


class AuthenticationTesting(TestCase):
    """
    Testing for authentication.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.post("/")
        self.request.session = {}
        setattr(self.request, "_messages", FallbackStorage(self.request))

    @patch("home.services.supabase.settings")
    def test_get_supabase_client_missing_env(self, mock_settings):
        """
        Test getting client when environment variables are not present.
        """
        mock_settings.SUPABASE_URL = None
        mock_settings.SUPABASE_KEY = None

        client = supabase.get_supabase_client()
        self.assertIsInstance(client, MagicMock)

    @patch("home.services.supabase.supabase_client.auth.sign_up")
    def test_supabase_sign_in_successful(self, mock_sign_up):
        """
        Test that user is successfully signed in.
        """
        mock_sign_up.return_value = MOCK_SIGN_UP
        result = supabase.supabase_sign_up(
            self.request, MOCK_USERNAME, MOCK_EMAIL, MOCK_PASSWORD
        )
        self.assertTrue(result)
        mock_sign_up.assert_called_once()

    @patch(
        "home.services.supabase.supabase_client.auth.sign_up",
        side_effect=Exception("fail"),
    )
    def test_signup_exception(self, _mock_signup):
        """
        Test that error is given if signup is unsuccessful.
        """
        result = supabase.supabase_sign_up(
            self.request, MOCK_USERNAME, MOCK_EMAIL, MOCK_PASSWORD
        )
        messages = list(get_messages(result))
        self.assertTrue(any("Error") in str(m) for m in messages)
        self.assertFalse(result)

    @patch("home.services.supabase.supabase_client.auth.sign_in_with_password")
    def test_supabase_log_in_successful(self, mock_log_in):
        """
        Test that user log in if correct information entered.
        """
        mock_response = MagicMock()
        mock_response.session.access_token = "token123"
        mock_response.user.user_metadata = {"username": MOCK_USERNAME}

        mock_log_in.return_value = mock_response

        result = supabase.supabase_log_in(self.request, MOCK_EMAIL, MOCK_PASSWORD)
        self.assertTrue(result)
        self.assertEqual(self.request.session["access_token"], "token123")
        self.assertEqual(self.request.session["supabase_username"], "user1234")

    @patch(
        "home.services.supabase.supabase_client.auth.sign_in_with_password",
        side_effect=Exception("fail"),
    )
    def test_login_exception(self, _mock_login):
        """
        Test that false is returned if error occurs on sign in.
        """
        result = supabase.supabase_log_in(self.request, MOCK_EMAIL, MOCK_PASSWORD)
        self.assertFalse(result)

    def test_is_valid_email_true(self):
        """
        Test that True is returned if valid email entered.
        """
        result = supabase.is_valid_email(self.request, MOCK_EMAIL)
        self.assertTrue(result)

    def test_is_valid_email_no_ending(self):
        """
        Test that False is returned if invalid email entered.
        """
        result = supabase.is_valid_email(self.request, "invalid")
        self.assertFalse(result)

    def test_is_valid_email_nothing_after_at(self):
        """
        Test that False is returned if invalid email entered.
        """
        result = supabase.is_valid_email(self.request, "invalid@")
        self.assertFalse(result)

    def test_is_valid_email_no_ending_of_email(self):
        """
        Test that False is returned if invalid email entered.
        """
        result = supabase.is_valid_email(self.request, "invalid@example")
        self.assertFalse(result)

    @patch("home.services.supabase.supabase_client.auth.get_user")
    def test_is_authenticated_true(self, mock_get_user):
        """
        Test that user with an account returns True.
        """
        self.request.session["access_token"] = "token123"
        mock_get_user.return_value = MOCK_GET_USER
        self.assertTrue(supabase.is_authenticated(self.request))

    @patch("home.services.supabase.supabase_client.auth.get_user")
    def test_is_authenticated_false(self, mock_get_user):
        """
        Test that user without an account returns False.
        """
        self.request.session["access_token"] = "token123"
        mock_get_user.side_effect = Exception("fail")
        self.assertFalse(supabase.is_authenticated(self.request))

    @patch("home.services.supabase.supabase_client.auth.sign_in_with_otp")
    def test_send_magic_link_successful(self, mock_sign_in_otp):
        """
        Test that user can get a like sent to them.
        """
        supabase.send_magic_link_login(self.request, MOCK_EMAIL)
        mock_sign_in_otp.assert_called_once()

    @patch(
        "home.services.supabase.supabase_client.auth.sign_in_with_otp",
        side_effect=Exception("fail"),
    )
    def test_magic_link_exception(self, _mock_otp):
        """
        Test exception is thrown if magic link fails to send.
        """
        request = self.client.request().wsgi_request
        supabase.send_magic_link_login(request, MOCK_EMAIL)
        messages = list(get_messages(request))
        self.assertTrue(any("Error:" in str(m) for m in messages))

    def test_reached_limit_magic_logins(self):
        """
        Test that once user reaches the max number of emails allowed, function returns False.
        """
        email = MOCK_EMAIL
        cache.clear()
        for _ in range(supabase.MAX_EMAILS_1_HOUR):
            self.assertFalse(supabase.reached_limit_magic_login(email))
        self.assertTrue(supabase.reached_limit_magic_login(email))

    @patch("home.services.supabase.supabase_client.auth.verify_otp")
    def test_get_user_magic_link_successful(self, mock_verify_otp):
        """
        Test that magic link can log a user in.
        """
        self.request.GET = {"token_hash": "token123"}
        mock_response = MagicMock()
        mock_response.session.access_token = "token123"
        mock_response.user.user_metadata = {"username": MOCK_USERNAME}

        mock_verify_otp.return_value = mock_response
        result = supabase.get_user_magic_link(self.request)
        self.assertTrue(result)
        self.assertEqual(self.request.session["access_token"], "token123")
        self.assertEqual(self.request.session["supabase_username"], "user1234")

    @patch("home.services.supabase.supabase_client.auth.verify_otp")
    def test_get_user_magic_link_unsuccessful(self, mock_verify_otp):
        """
        Test that if invalid token, user cannot be signed in.
        """
        self.request.GET = {"token_hash": "token123"}
        mock_verify_otp.side_effect = Exception("Invalid OTP")

        result = supabase.get_user_magic_link(self.request)
        self.assertFalse(result)
        self.assertNotIn("access_token", self.request.session)

    def test_magic_link_no_token(self):
        """
        Test that error if there is no token.
        """
        request = self.client.request().wsgi_request
        request.GET = {}
        result = supabase.get_user_magic_link(request)
        self.assertFalse(result)
        messages = list(get_messages(request))
        self.assertTrue(any("Please try again" in str(m) for m in messages))

    def test_get_user_id_successful(self):
        """
        Test sucessful retrieval of user id if it was in session.
        """
        self.request.session["supabase_user_id"] = MOCK_GET_USER["user"]["id"]
        result = supabase.get_user_id(self.request)
        self.assertEqual(result, MOCK_GET_USER["user"]["id"])

    def test_get_user_id_unsuccessful(self):
        """
        Test unsuccessful result if user id is not in session.
        """
        result = supabase.get_user_id(self.request)
        self.assertIsNone(result)


class SupabaseWatchlistTest(TestCase):
    """
    Testing the watchlist feature that is implemented in Supabase storage.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/")
        self.request.session = {}
        self.user_id = MOCK_GET_USER["user"]["id"]
        self.movie_id = 550

    @patch("home.services.supabase.supabase_client")
    def test_insert_in_watchlist_success(self, mock_client):
        """
        Test successful  insert into watchlist.
        """
        mock_table = mock_client.table.return_value
        mock_table.insert.return_value.execute.return_value = True

        success, msg = supabase.insert_in_watchlist(self.user_id, self.movie_id)
        self.assertTrue(success)
        self.assertIn("Succesfully added", msg)

    @patch("home.services.supabase.supabase_client")
    def test_insert_in_watchlist_duplicate(self, mock_client):
        """
        Test user cannot add same movie to watchlist.
        """
        mock_table = mock_client.table.return_value
        mock_table.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        success, msg = supabase.insert_in_watchlist(self.user_id, self.movie_id)
        self.assertFalse(success)
        self.assertIn("already in watchlist", msg)

    @patch("home.services.supabase.supabase_client")
    def test_delete_in_watchlist_success(self, mock_client):
        """
        Test user can successfully delete a movie from the watchlist.
        """
        mock_table = mock_client.table.return_value
        mock_table.delete.return_value.eq.return_value.eq.return_value.execute.return_value = True

        result = supabase.delete_in_watchlist(self.user_id, self.movie_id)
        self.assertTrue(result)

    @patch("home.services.supabase.supabase_client")
    def test_delete_in_watchlist_failure(self, mock_client):
        """
        Test that False is returned if there is an error with deletion.
        """
        mock_table = mock_client.table.return_value
        delete_chain = (
            mock_table.delete.return_value.eq.return_value.eq.return_value.execute
        )
        delete_chain.side_effect = Exception("DB error")
        result = supabase.delete_in_watchlist(self.user_id, self.movie_id)
        self.assertFalse(result)

    @patch("home.services.supabase.supabase_client")
    def test_get_watchlist_returns_movies(self, mock_client):
        """
        Test that several movies can be returned.
        """
        mock_table = mock_client.table.return_value
        mock_response = MagicMock()
        mock_response.data = [{"movie_id": 1}, {"movie_id": 2}]
        mock_table.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        movies = supabase.get_watchlist(self.user_id)
        self.assertEqual(movies, [1, 2])

    @patch("home.services.supabase.supabase_client")
    def test_get_watchlist_with_specific_movie(self, mock_client):
        """
        Test that a single movie can be specified to return.
        """
        mock_table = mock_client.table.return_value
        mock_response = MagicMock()
        mock_response.data = [{"movie_id": self.movie_id}]
        select_chain = (
            mock_table.select.return_value.eq.return_value.eq.return_value.execute
        )
        select_chain.return_value = mock_response

        movies = supabase.get_watchlist(self.user_id, movie_id=self.movie_id)
        self.assertEqual(movies, [self.movie_id])

    @patch("home.services.supabase.supabase_client")
    def test_get_watchlist_exception_returns_empty(self, mock_client):
        """
        Test that empty list is returned if there is an error.
        """
        mock_table = mock_client.table.return_value
        mock_table.select.return_value.eq.return_value.execute.side_effect = Exception(
            "DB error"
        )

        movies = supabase.get_watchlist(self.user_id)
        self.assertEqual(movies, [])

    @patch("home.services.supabase.supabase_client")
    def test_get_watchlist_empty_list_when_no_movies(self, mock_client):
        """
        Test empty list is returned when no movies in watchlist.
        """
        mock_table = mock_client.table.return_value
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        result = supabase.get_watchlist(self.user_id)
        assert result == []


class SupabaseAccountsTests(TestCase):
    """
    Testing for supabase accounts through integreation and unit tests.
    """

    def setUp(self):
        self.request = MagicMock()
        self.request.session = {
            "access_token": "access",
            "refresh_token": "refresh",
            "supabase_username": "oldname",
        }
        self.user_id = MOCK_GET_USER["user"]["id"]

    @patch("home.services.supabase.get_user_supabase_client")
    def test_change_username_success(self, mock_get_client):
        """
        Test ability to change username through supabase.
        """

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.auth.update_user.return_value = MagicMock()

        result = supabase.change_user_information(
            {"data": {"username": MOCK_USERNAME}}, self.request
        )

        self.assertTrue(result)
        self.assertEqual(self.request.session["supabase_username"], MOCK_USERNAME)

        mock_get_client.assert_called_once_with("access", "refresh")
        mock_client.auth.update_user.assert_called_once()

    @patch("home.services.supabase.get_user_supabase_client")
    def test_change_password_success(self, mock_get_client):
        """
        Test ability to change password through supabase.
        """

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.auth.update_user.return_value = MagicMock()

        result = supabase.change_user_information(
            {"password": "newpass123"}, self.request
        )

        self.assertTrue(result)
        mock_get_client.assert_called_once_with("access", "refresh")
        mock_client.auth.update_user.assert_called_once()

        self.assertEqual(self.request.session.get("supabase_username"), "oldname")

    @patch("home.services.supabase.supabase_client")
    def test_change_username_failure(self, mock_client):
        """
        Test failure to change username.
        """
        mock_client.auth.update_user.return_value = False

        result = supabase.change_user_information(
            {"data": {"username": "fail"}}, self.request
        )

        self.assertFalse(result)

    @patch("home.services.supabase.supabase_client")
    def test_change_user_exception(self, mock_client):
        """
        Test if there is an exception.
        """
        mock_client.auth.update_user.side_effect = Exception("boom")

        result = supabase.change_user_information(
            {"data": {"username": "error"}}, self.request
        )

        self.assertFalse(result)

    @patch("home.services.supabase.Movie.objects.filter")
    @patch("home.services.supabase.supabase_admin.auth.admin.delete_user")
    def test_delete_user_success(self, mock_delete_user, mock_filter):
        """
        Test user can successfully be deleted.
        """
        self.request.session = MagicMock()
        self.request.session.get.return_value = self.user_id
        self.request.session.flush = MagicMock()

        mock_delete_user.return_value = MagicMock()

        mock_queryset = MagicMock()
        mock_filter.return_value = mock_queryset
        mock_queryset.delete.return_value = (1, {})

        result = supabase.delete_user_from_supabase(self.request)

        self.assertTrue(result)

        mock_delete_user.assert_called_once_with(self.user_id)
        mock_filter.assert_called_once_with(user=self.user_id)
        mock_queryset.delete.assert_called_once()
        self.request.session.flush.assert_called_once()

    @patch("home.services.supabase.supabase_admin.auth.admin.delete_user")
    def test_delete_user_failure(self, mock_delete):
        """
        Test correct resopnse if user deletion fails.
        """
        self.request.session = {"supabase_user_id": self.user_id}

        mock_delete.side_effect = Exception("fail")
        result = supabase.delete_user_from_supabase(self.request)
        self.assertFalse(result)

    def test_delete_user_missing_session(self):
        """
        Test failure if missions session.
        """
        self.request.session = {}
        result = supabase.delete_user_from_supabase(self.request)
        self.assertFalse(result)
