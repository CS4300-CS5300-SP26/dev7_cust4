from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase, RequestFactory
from home.services import supabase
from unittest.mock import patch, MagicMock
from django.core.cache import cache


MOCK_SIGN_UP = {
  "user": {
    "id": "11111111-1111-1111-1111-111111111111",
    "user_metadata": {
        "username": "user1234"
    },
    "aud": "authenticated",
    "email": "email@example.com",
  }
}

MOCK_GET_USER = {
  "user": {
    "id": "11111111-1111-1111-1111-111111111111",
    "app_metadata": {
      "provider": "email",
      "providers": []
    },
    "email": "email@example.com",
  }
}

MOCK_USERNAME = MOCK_SIGN_UP["user"]["user_metadata"]["username"]
MOCK_EMAIL = MOCK_SIGN_UP["user"]["email"]
MOCK_PASSWORD = "Test1234!!"
class CreateSession(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.post("/")
        self.request.session = {}
        self.request._messages = FallbackStorage(self.request)

    @patch("home.services.supabase.supabase_client.auth.sign_up")
    @patch("home.services.supabase.supabase_log_in", return_value=True)
    def test_supabase_sign_in_successful(self, mock_log_in, mock_sign_up):
        """
        Test that user is successfully signed in.
        """
        mock_sign_up.return_value = MOCK_SIGN_UP
        result = supabase.supabase_sign_up(self.request, MOCK_USERNAME, MOCK_EMAIL, MOCK_PASSWORD)
        self.assertTrue(result)
        mock_sign_up.assert_called_once()

    @patch("home.services.supabase.supabase_client.auth.sign_in_with_password")
    def test_supabase_log_in_successful(self, mock_log_in):
        """
        Test that user log in if correct information entered.
        """
        mock_response = MagicMock()
        mock_response.session.access_token = "1111111-111111"
        mock_response.user.user_metadata = {"username": MOCK_USERNAME}

        mock_log_in.return_value = mock_response

        result = supabase.supabase_log_in(self.request, MOCK_EMAIL, MOCK_PASSWORD)
        self.assertTrue(result)
        self.assertEqual(self.request.session["access_token"], "1111111-111111")
        self.assertEqual(self.request.session["supabase_username"], "user1234")
        
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
        self.request.session["access_token"] = "1111111-111111"
        mock_get_user.return_value = MOCK_GET_USER
        self.assertTrue(supabase.is_authenticated(self.request))

    @patch("home.services.supabase.supabase_client.auth.get_user")
    def test_is_authenticated_false(self, mock_get_user):
        """
        Test that user without an account returns False.
        """
        self.request.session["access_token"] = "1111111-111111"
        mock_get_user.side_effect = Exception("fail")
        self.assertFalse(supabase.is_authenticated(self.request))

    @patch("home.services.supabase.supabase_client.auth.sign_in_with_otp")
    def test_send_magic_link_successful(self, mock_sign_in_otp):
        supabase.send_magic_link_login(self.request, MOCK_EMAIL)
        mock_sign_in_otp.assert_called_once()

    def test_reached_limit_magic_logins(self):
        """
        Test that once user reaches the max number of emails allowed, function returns False.
        """
        email = MOCK_EMAIL
        cache.clear()
        for i in range(supabase.MAX_EMAILS_1_HOUR):
            self.assertFalse(supabase.reached_limit_magic_login(email))
        self.assertTrue(supabase.reached_limit_magic_login(email))

    @patch("home.services.supabase.supabase_client.auth.verify_otp")
    def test_get_user_magic_link_successful(self, mock_verify_otp):
        self.request.GET = {"token_hash": "token123"}
        mock_response = MagicMock()
        mock_response.session.access_token = "1111111-111111"
        mock_response.user.user_metadata = {"username": MOCK_USERNAME}

        mock_verify_otp.return_value = mock_response
        result = supabase.get_user_magic_link(self.request)
        self.assertTrue(result)
        self.assertEqual(self.request.session["access_token"], "1111111-111111")
        self.assertEqual(self.request.session["supabase_username"], "user1234")

    
    @patch("home.services.supabase.supabase_client.auth.verify_otp")
    def test_get_user_magic_link_unsuccessful(self, mock_verify_otp):
        self.request.GET = {"token_hash": "token123"}
        mock_verify_otp.side_effect = Exception("Invalid OTP")

        result = supabase.get_user_magic_link(self.request)
        self.assertFalse(result)
        self.assertNotIn("access_token", self.request.session)
