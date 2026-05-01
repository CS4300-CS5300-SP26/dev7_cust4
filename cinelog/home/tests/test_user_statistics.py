# pylint: disable=no-member
from unittest.mock import patch
from datetime import timedelta
from django.test import TestCase
from django.utils.timezone import now
from home.models import Movie
from home.services import user_statistics


class StatsServiceTest(TestCase):
    """
    Testing for user statistics shown on account.
    """

    def setUp(self):
        self.user_id = "11111111-1111-1111-1111-111111111111"

    @patch(
        "home.services.user_statistics.supabase.get_watchlist", return_value=[1, 2, 3]
    )
    def test_watchlist_size_returns_correct_count(self, mock_watchlist):
        """
        Test that the correct number of movies in the watchlist is returned.
        """
        self.assertEqual(user_statistics.get_size_of_watchlist(self.user_id), 3)
        mock_watchlist.assert_called_once_with(self.user_id)

    @patch("home.services.user_statistics.supabase.get_watchlist", return_value=[])
    def test_watchlist_size_empty(self, _mock_watchlist):
        """
        Test 0 is returned if no movies in watchlist
        """
        self.assertEqual(user_statistics.get_size_of_watchlist(self.user_id), 0)

    @patch("home.services.user_statistics.supabase.get_watchlist", return_value=None)
    def test_watchlist_size_none_handling(self, _mock_watchlist):
        """
        Test if supabase returns None instead of list with movie ids.
        """
        with self.assertRaises(TypeError):
            user_statistics.get_size_of_watchlist(self.user_id)

    def test_library_size_counts_movies(self):
        """
        Test correct number of movies returned when library counted.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1)
        Movie.objects.create(user=self.user_id, tmdb_id=2)

        self.assertEqual(user_statistics.get_size_of_library(self.user_id), 2)

    def test_library_size_empty(self):
        """
        Test if no movies are in library.
        """
        self.assertEqual(user_statistics.get_size_of_library(self.user_id), 0)

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_runtime_hours_conversion(self, mock_tmdb):
        """
        Test runtime is calculated correctly in hours and minutes format.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1)
        Movie.objects.create(user=self.user_id, tmdb_id=2)

        mock_tmdb.side_effect = [
            {"runtime": 90},
            {"runtime": 110},
        ]
        result = user_statistics.get_num_hours_in_library(self.user_id)
        self.assertEqual(result, "3h 20m")

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_runtime_missing_runtime(self, mock_tmdb):
        """
        Test if runtime is not available for the movie, so API returns None.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1)
        mock_tmdb.return_value = {}

        result = user_statistics.get_num_hours_in_library(self.user_id)
        self.assertEqual(result, "0h 0m")

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_runtime_no_movies(self, mock_tmdb):
        """
        Test if there are no movies in the library.
        """
        result = user_statistics.get_num_hours_in_library(self.user_id)
        self.assertEqual(result, "0h 0m")
        mock_tmdb.assert_not_called()

    def test_monthly_logged_movies_shape(self):
        """
        Test the correct form of data that is returned.
        """
        result = user_statistics.get_monthly_logged_movies(self.user_id)
        self.assertEqual(len(result), 12)
        for item in result:
            self.assertIn("height", item)
            self.assertIn("value", item)

    def test_monthly_logged_movies_all_zero_edge(self):
        """
        Test if there are no movies logged, but still should have default values.
        """
        result = user_statistics.get_monthly_logged_movies(self.user_id)
        for item in result:
            self.assertEqual(item["value"], 0)
            self.assertEqual(item["height"], 5)

    def test_logged_monthly_average_normal(self):
        """
        Test calculation of monthly average logged movies.
        """
        with patch(
            "home.services.user_statistics.get_library_months_for_year",
            return_value=[1, 2, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        ):
            self.assertEqual(
                user_statistics.get_logged_monthly_average(self.user_id), 1
            )  # 16 // 12 = 1

    def test_logged_monthly_average_empty(self):
        """
        Test no movies in library, so 0 average.
        """
        with patch(
            "home.services.user_statistics.get_library_months_for_year", return_value=[]
        ):
            self.assertEqual(
                user_statistics.get_logged_monthly_average(self.user_id), 0
            )

    def test_days_logged_counts_one_day(self):
        """
        Test days logged returns total number of days a movie was added to
        logger if only have 1 day added movies.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1, created_at=now())
        Movie.objects.create(user=self.user_id, tmdb_id=2, created_at=now())
        self.assertEqual(user_statistics.get_days_logged(self.user_id), 1)

    def test_days_logged_counts_multiple_days(self):
        """
        Test days logged returns correct number of unique days when movies are
        logged on different dates.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1, created_at=now())
        Movie.objects.create(
            user=self.user_id, tmdb_id=2, created_at=now() - timedelta(days=1)
        )
        Movie.objects.create(
            user=self.user_id, tmdb_id=3, created_at=now() - timedelta(days=2)
        )

        self.assertEqual(user_statistics.get_days_logged(self.user_id), 3)

    def test_days_logged_none(self):
        """
        Test if no movies are in logger.
        """
        self.assertEqual(user_statistics.get_days_logged(self.user_id), 0)

    def test_average_rating_normal(self):
        """
        Test average rating calculation without rounding.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1, rating=8)
        Movie.objects.create(user=self.user_id, tmdb_id=2, rating=6)
        self.assertEqual(user_statistics.get_average_rating(self.user_id), 7.0)

    def test_average_rating_rounding(self):
        """
        Test average rating calculation with rounding.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1, rating=7)
        Movie.objects.create(user=self.user_id, tmdb_id=2, rating=8)
        self.assertEqual(user_statistics.get_average_rating(self.user_id), 7.5)

    def test_average_rating_empty(self):
        """
        Test if have no movies, rating is 0.
        """
        self.assertEqual(user_statistics.get_average_rating(self.user_id), 0)

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_genre_statistics_no_other_when_exact_100(self, mock_tmdb):
        """
        Test other category is 0 when percent is 100.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1)
        Movie.objects.create(user=self.user_id, tmdb_id=2)

        mock_tmdb.side_effect = [
            {"genres": [{"name": "Action"}, {"name": "Drama"}]},
            {"genres": [{"name": "Action"}]},
        ]

        top, data = user_statistics.get_genre_statistics(self.user_id)
        self.assertEqual(top, "Action")
        self.assertEqual(len(data), 3)

        genre_names = [g["genre_name"] for g in data]
        self.assertIn("Action", genre_names)
        self.assertIn("Drama", genre_names)
        self.assertIn("Other", genre_names)
        genre_map = {g["genre_name"]: g for g in data}
        self.assertEqual(genre_map["Other"]["percent"], 0)

    @patch(
        "home.services.user_statistics.tmdb.fetch_movie_detail",
        return_value={"genres": []},
    )
    def test_genre_statistics_no_genres(self, _mock_tmdb):
        """
        Test if no generes for the movies.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1)

        top, data = user_statistics.get_genre_statistics(self.user_id)
        self.assertIsNone(top)
        self.assertEqual(data, [])

    def test_genre_statistics_no_movies(self):
        """
        Test if no movies in logger.
        """
        top, data = user_statistics.get_genre_statistics(self.user_id)

        self.assertIsNone(top)
        self.assertEqual(data, [])

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_genre_statistics_missing_genre_names(self, mock_tmdb):
        """
        Test if the movie has no genere.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1)

        mock_tmdb.return_value = {"genres": [{"id": 1}]}  # no name field

        top, data = user_statistics.get_genre_statistics(self.user_id)

        self.assertIsNone(top)
        self.assertEqual(data, [])

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_returns_top_five_movies_by_rating(self, mock_tmdb):
        """
        Test top 5 rated movies returned if several movies.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1, rating=1)
        Movie.objects.create(user=self.user_id, tmdb_id=2, rating=2)
        Movie.objects.create(user=self.user_id, tmdb_id=3, rating=3)
        Movie.objects.create(user=self.user_id, tmdb_id=4, rating=4)
        Movie.objects.create(user=self.user_id, tmdb_id=5, rating=5)
        Movie.objects.create(user=self.user_id, tmdb_id=6, rating=2)

        mock_tmdb.side_effect = [
            {"id": 5, "title": "Movie 5"},
            {"id": 4, "title": "Movie 4"},
            {"id": 3, "title": "Movie 3"},
            {"id": 2, "title": "Movie 2"},
            {"id": 6, "title": "Movie 6"},
        ]

        result = user_statistics.get_top_five_movies(self.user_id)

        self.assertEqual(len(result), 5)
        self.assertEqual(result[0]["id"], 5)
        self.assertEqual(result[1]["id"], 4)
        self.assertEqual(result[4]["id"], 6)

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_returns_all_movies_if_less_than_five(self, mock_tmdb):
        """
        Test all movies are returned if have less than 5 movies in library.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1, rating=10)
        Movie.objects.create(user=self.user_id, tmdb_id=2, rating=8)

        mock_tmdb.side_effect = [
            {"id": 1, "title": "A"},
            {"id": 2, "title": "B"},
        ]
        result = user_statistics.get_top_five_movies(self.user_id)
        self.assertEqual(len(result), 2)

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_returns_empty_list_when_no_movies(self, mock_tmdb):
        """
        Test no movies returned if library is empty.
        """
        result = user_statistics.get_top_five_movies(self.user_id)
        self.assertEqual(result, [])
        mock_tmdb.assert_not_called()

    @patch("home.services.user_statistics.tmdb.fetch_movie_detail")
    def test_skips_movies_when_tmdb_returns_none(self, mock_tmdb):
        """
        Test that movie is not counted if no response from TMDB.
        """
        Movie.objects.create(user=self.user_id, tmdb_id=1, rating=10)
        Movie.objects.create(user=self.user_id, tmdb_id=2, rating=9)

        mock_tmdb.side_effect = [
            None,
            {"id": 2, "title": "Movie 2"},
        ]

        result = user_statistics.get_top_five_movies(self.user_id)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 2)
