import requests
from django.conf import settings

BASE_URL = "https://api.themoviedb.org/3"
TMDB_KEY = settings.TMDB_API_KEY


def fetch_movies(endpoint):
    """
    Fetch a list of movies from a TMDB movie endpoint.

    Args:
        endpoint (str): TMDB movie endpoint to query.

    Returns:
        list: A list of movie dicts from the API response.
        Returns an empty list if request fails.
    """
    url = f"{BASE_URL}/movie/{endpoint}"
    params = {
        "api_key": TMDB_KEY,
        "language": "en-US",
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.RequestException:
        return []


def fetch_movie_detail(movie_id):
    """
    Get full details for a movie by its TMDB ID.

    Args:
        movie_id (int): TMDB movie ID.

    Returns:
        dict: A dict containing movie details including genres, runtime,
              overview, backdrop_path, poster_path, and credits.
        Returns an empty dict if the request fails.
    """
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {
        "api_key": TMDB_KEY,
        "append_to_response": "credits",
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}