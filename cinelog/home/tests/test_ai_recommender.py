from unittest.mock import patch, MagicMock
from django.test import TestCase
from home.services.ai_rec import get_movie_recommendation


class AIRecommendationTest(TestCase):
    """
    Tests for the AI recommender feature.
    """

    def setUp(self):
        """Set up reusable test data."""
        self.genres = ["Thriller", "Drama"]
        self.era = "modern"
        self.person = "Christopher Nolan"
        self.awards = ["Academy Award Winner"]
        self.excluded_titles = ["Inception", "The Dark Knight"]
        self.liked_movies = [
            {"title": "Memento", "rating": 5},
            {"title": "Interstellar", "rating": 4},
        ]

    def _mock_openai_response(self, content):
        """
        Helper that builds a fake OpenAI response object.
        Avoids repeating the same mock setup in every test.
        """
        mock_message = MagicMock()
        mock_message.choices[0].message.content = content
        mock_message.choices[0].finish_reason = "stop"
        return mock_message

    @patch("home.services.ai_rec.OpenAI")
    def test_returns_list_of_movies(self, mock_openai):
        """
        Test that a valid OpenAI response returns a list of movie dicts.
        """
        fake_response = (
            '[{"title": "Zodiac", "year": "2007", "reason": "Great thriller."}]'
        )
        mock_openai.return_value.chat.completions.create.return_value = (
            self._mock_openai_response(fake_response)
        )

        result = get_movie_recommendation(self.genres, self.era, self.person)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Zodiac")

    @patch("home.services.ai_rec.OpenAI")
    def test_returns_multiple_movies(self, mock_openai):
        """
        Test that multiple movies are returned when AI gives a full list.
        """
        fake_response = (
            '[{"title": "Zodiac", "year": "2007", "reason": "..."},'
            '{"title": "Se7en", "year": "1995", "reason": "..."}]'
        )
        mock_openai.return_value.chat.completions.create.return_value = (
            self._mock_openai_response(fake_response)
        )

        result = get_movie_recommendation(self.genres, self.era, self.person)

        self.assertEqual(len(result), 2)

    @patch("home.services.ai_rec.OpenAI")
    def test_fallback_on_invalid_json(self, mock_openai):
        """
        Test that a fallback error movie is returned when AI returns invalid JSON.
        """
        mock_openai.return_value.chat.completions.create.return_value = (
            self._mock_openai_response("not valid json at all")
        )

        result = get_movie_recommendation(self.genres, self.era, self.person)

        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["title"], "Could not generate recommendation")

    @patch("home.services.ai_rec.OpenAI")
    def test_fallback_on_empty_response(self, mock_openai):
        """
        Test fallback when AI returns an empty string.
        """
        mock_openai.return_value.chat.completions.create.return_value = (
            self._mock_openai_response("")
        )

        result = get_movie_recommendation(self.genres, self.era, self.person)

        self.assertEqual(result[0]["title"], "Could not generate recommendation")

    @patch("home.services.ai_rec.OpenAI")
    def test_strips_markdown_code_fences(self, mock_openai):
        """
        Test that markdown code fences are stripped before parsing.
        """
        fake_response = (
            '```json\n[{"title": "Zodiac", "year": "2007", "reason": "..."}]\n```'
        )
        mock_openai.return_value.chat.completions.create.return_value = (
            self._mock_openai_response(fake_response)
        )

        result = get_movie_recommendation(self.genres, self.era, self.person)

        self.assertEqual(result[0]["title"], "Zodiac")

    @patch("home.services.ai_rec.OpenAI")
    def test_excluded_titles_included_in_prompt(self, mock_openai):
        """
        Test that excluded titles are passed into the prompt so AI avoids them.
        """
        fake_response = '[{"title": "Zodiac", "year": "2007", "reason": "..."}]'
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = self._mock_openai_response(
            fake_response
        )

        get_movie_recommendation(
            self.genres, self.era, self.person, excluded_titles=self.excluded_titles
        )

        # check the prompt sent to OpenAI contains the excluded titles
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        self.assertIn("Inception", prompt)
        self.assertIn("The Dark Knight", prompt)

    @patch("home.services.ai_rec.OpenAI")
    def test_liked_movies_included_in_prompt(self, mock_openai):
        """
        Test that liked movies from user history are passed into the prompt.
        """
        fake_response = '[{"title": "Zodiac", "year": "2007", "reason": "..."}]'
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = self._mock_openai_response(
            fake_response
        )

        get_movie_recommendation([], "", "", liked_movies=self.liked_movies)

        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        self.assertIn("Memento", prompt)
        self.assertIn("Interstellar", prompt)

    @patch("home.services.ai_rec.OpenAI")
    def test_no_preferences_uses_default(self, mock_openai):
        """
        Test that passing no preferences defaults to 'any genre, any era' in prompt.
        """
        fake_response = '[{"title": "Zodiac", "year": "2007", "reason": "..."}]'
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.return_value = self._mock_openai_response(
            fake_response
        )

        get_movie_recommendation([], "", "")

        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        self.assertIn("any genre, any era", prompt)

    @patch("home.services.ai_rec.OpenAI")
    def test_result_contains_required_keys(self, mock_openai):
        """
        Test that every movie in the result has title, year, and reason keys.
        """
        fake_response = '[{"title": "Zodiac", "year": "2007", "reason": "Great film."}]'
        mock_openai.return_value.chat.completions.create.return_value = (
            self._mock_openai_response(fake_response)
        )

        result = get_movie_recommendation(self.genres, self.era, self.person)

        for movie in result:
            self.assertIn("title", movie)
            self.assertIn("year", movie)
            self.assertIn("reason", movie)
