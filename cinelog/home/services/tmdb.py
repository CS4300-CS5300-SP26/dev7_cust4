"""Service functions for interacting with the TMDB API."""
import logging
import requests
from django.conf import settings

BASE_URL = "https://api.themoviedb.org/3"
logger = logging.getLogger(__name__)
TMDB_KEY = settings.TMDB_API_KEY


def fetch_movies(endpoint, single=False):
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
        if single:
            return data
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
    except requests.RequestException as exc:
        logger.error("Failed to fetch movie detail for movie %s: %s", movie_id, exc)
        return {}


def get_cast(movie, limit=10):
    """
    Extract cast members from an already-fetched movie dict.

    Returns:
        list: A list of cast member dicts.
    """
    movie_credits = movie.get("credits", {})
    return movie_credits.get("cast", [])[:limit]


def get_director(movie):
    """
    Extract the director from an already-fetched movie dict.

    Returns:
        dict or None: Director crew member dict or None.
    """
    crew = movie.get("credits", {}).get("crew", [])
    return next((member for member in crew if member["job"] == "Director"), None)


def search_movies(query):
    """
    Search for movies using the TMDB search API

    query: The movie title being searched

    returns: list of movie dicts matching the search query/ empty list if there is no match
    """
    url = f"{BASE_URL}/search/movie"
    params = {"api_key": TMDB_KEY, "language": "en-US", "query": query, "page": 1}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.RequestException:
        return []


def get_movie_trailer(movie_id):
    """
    Fetch trailer for specific movie via TMDB movie ID.

    returns: dict OR None: The first YouTube trailer video dict, or None if not found.
    """
    url = f"{BASE_URL}/movie/{movie_id}/videos"

    try:
        response = requests.get(url, params={"api_key": TMDB_KEY}, timeout=5)
        response.raise_for_status()
        videos = response.json().get("results", [])

        trailer = next(
            (v for v in videos if v["type"] == "Trailer" and v["site"] == "YouTube"),
            None,
        )
        return trailer
    except requests.RequestException:
        return None


def get_watch_providers(movie_id, country="US"):
    """
    Fetch streaming, rental, and purchase providers for a movie.

    Args:
        movie_id (int): TMDB movie ID.
        country (str): ISO 3166-1 country code (default "US").

    Returns:
        dict: Keys 'streaming', 'rent', 'buy' — each a list of provider dicts.
              Returns empty dict if not available or request fails.
    """
    url = f"{BASE_URL}/movie/{movie_id}/watch/providers"
    try:
        response = requests.get(url, params={"api_key": TMDB_KEY}, timeout=5)
        response.raise_for_status()
        results = response.json().get("results", {})
        country_data = results.get(country, {})
        return {
            "streaming": country_data.get("flatrate", []),
            "rent": country_data.get("rent", []),
            "buy": country_data.get("buy", []),
            "link": country_data.get("link", ""),
        }
    except requests.RequestException as exc:
        logger.error("Failed to fetch movie detail for movie %s: %s", movie_id, exc)
        return {}


def fetch_ratings(tmdb_movie):
    """
    Fetch audience (TMDB) and critic (Rotten Tomatoes via OMDB) ratings
    for a movie.

    Adds the following keys to a copy of the input dict:
      - audience_score (float | None): TMDB vote_average on a 0-10 scale.
      - critic_score (int | None): Rotten Tomatoes score as an integer 0-100.
      - critic_score_display (str | None): Human-readable RT score, e.g. "74%".

    Args:
        tmdb_movie (dict): A TMDB movie result dict (must have 'title' and
            optionally 'release_date').

    Returns:
        dict: A new dict (shallow copy) with rating keys added.
    """
    import copy
    from django.conf import settings as django_settings

    movie = copy.copy(tmdb_movie)

    # Audience score from TMDB (0-10). Explicitly check for None so a
    # legitimate score of 0 is preserved rather than treated as falsy.
    raw = movie.get("vote_average")
    movie["audience_score"] = round(float(raw), 1) if raw is not None else None

    # Critic score from OMDB (Rotten Tomatoes %)
    omdb_key = getattr(django_settings, "OMDB_API_KEY", "")
    movie["critic_score"] = None
    movie["critic_score_display"] = None

    if omdb_key:
        title = movie.get("title", "")
        release_date = movie.get("release_date")
        year = str(release_date)[:4] if release_date else ""
        params = {"apikey": omdb_key, "t": title, "type": "movie"}
        if year:
            params["y"] = year
        try:
            resp = requests.get("https://www.omdbapi.com/", params=params, timeout=5)
            resp.raise_for_status()
            try:
                data = resp.json()
            except ValueError as exc:
                logger.error("OMDB returned non-JSON for '%s': %s", title, exc)
                return movie
            if data.get("Response") == "True":
                for rating in data.get("Ratings", []):
                    if rating.get("Source") == "Rotten Tomatoes":
                        # Normalize "74%", "74/100", or plain "74"
                        raw_val = rating["Value"].replace("%", "").strip()
                        numeric = raw_val.split("/")[0].strip()
                        if numeric.isdigit():
                            movie["critic_score"] = int(numeric)
                            movie["critic_score_display"] = f"{numeric}%"
                        break
        except requests.RequestException as exc:
            logger.error("OMDB fetch failed for '%s': %s", title, exc)

    return movie
