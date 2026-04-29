import uuid
import json
import datetime
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from home.models import Movie


class CalendarViewTest(TestCase):
    """
    Test for calendar views and API behavior.
    """
    def setUp(self):
        self.client = Client()
        self.user_id = str(uuid.uuid4())

    @patch("home.views.supabase.get_user_id")
    def test_calendar_view_redirects_if_not_logged_in(self, mock_get_user_id):
        """
        Test calendar view redirects to login if user is not authenticated.
        """
        mock_get_user_id.return_value = None
        response = self.client.get(reverse("calendar"))
        self.assertRedirects(response, reverse("login"))

    @patch("home.views.supabase.get_user_id")
    def test_calendar_view_loads_for_logged_in_user(self, mock_get_user_id):
        """
        Test calendar page loads successfully for logged-in users
        """
        mock_get_user_id.return_value = self.user_id
        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "calendar.html")

    @patch("home.views.supabase.get_user_id")
    def test_calendar_events_api_returns_json(self, mock_get_user_id):
        """
        Test calendar events API returns a JSON response.
        """
        mock_get_user_id.return_value = self.user_id
        response = self.client.get(reverse("calendar_events"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    @patch("home.views.supabase.get_user_id")
    def test_calendar_events_api_redirects_if_not_logged_in(self, mock_get_user_id):
        """
        Test calendar events API returns empty list if user is not logged in.
        """
        mock_get_user_id.return_value = None
        response = self.client.get(reverse("calendar_events"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data, [])

    @patch("home.views.supabase.get_user_id")
    def test_calendar_events_only_shows_movies_with_dates(self, mock_get_user_id):
        """
        Test only movies with watched date are returned in calendar events.
        """
        mock_get_user_id.return_value = self.user_id

        # Movie with a watch date
        Movie.objects.create(
            user=self.user_id,
            title="Interstellar",
            tmdb_id=157336,
            rating=5,
            watched_date=datetime.date(2024, 1, 15),
        )
        # Movie without a watch date
        Movie.objects.create(
            user=self.user_id,
            title="Inception",
            tmdb_id=27205,
            rating=4,
            watched_date=None,
        )

        response = self.client.get(reverse("calendar_events"))
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Interstellar")
        self.assertEqual(data[0]["start"], "2024-01-15")


class WatchedDateTest(TestCase):
    """
    Test for watched date functionality.
    """

    def setUp(self):
        self.client = Client()
        self.user_id = str(uuid.uuid4())

    @patch("home.views.supabase.get_user_id")
    def test_edit_movie_saves_watched_date(self, mock_get_user_id):
        """
        Test editing a movie correctly saves the watched date.
        """

        mock_get_user_id.return_value = self.user_id

        movie = Movie.objects.create(
            user=self.user_id,
            title="Interstellar",
            tmdb_id=157336,
            rating=3,
        )

        response = self.client.post(
            reverse("edit_movie"),
            {
                "movie_id": movie.id,
                "rating": 5,
                "notes": "Great film",
                "watched_date": "2024-01-15",
            },
        )

        movie.refresh_from_db()
        self.assertEqual(movie.watched_date, datetime.date(2024, 1, 15))
        self.assertRedirects(response, reverse("library"))

    @patch("home.views.supabase.get_user_id")
    def test_edit_movie_clears_watched_date(self, mock_get_user_id):
        """
        Test editing a movie clears the watched date when empty.
        """
        mock_get_user_id.return_value = self.user_id

        movie = Movie.objects.create(
            user=self.user_id,
            title="Interstellar",
            tmdb_id=157336,
            rating=3,
            watched_date=datetime.date(2024, 1, 15),
        )

        self.client.post(
            reverse("edit_movie"),
            {
                "movie_id": movie.id,
                "rating": 3,
                "notes": "",
                "watched_date": "",
            },
        )

        movie.refresh_from_db()
        self.assertIsNone(movie.watched_date)
