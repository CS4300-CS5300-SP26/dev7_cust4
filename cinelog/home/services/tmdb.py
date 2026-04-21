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


def discover_movies_by_filters_only(filters):
    """
    Discover movies using ONLY filters (no title search).
    Uses TMDB Discover endpoint for filter-only queries.
    
    Args:
        filters (dict): Filter parameters including:
            - genres: List of genre names
            - actor: Actor name
            - rating_min: Minimum rating
            - rating_max: Maximum rating
            - year: Release year
    
    Returns:
        list: A list of movie dicts matching the filters
    """
    url = f"{BASE_URL}/discover/movie"
    
    params = {
        "api_key": TMDB_KEY,
        "language": "en-US",
        "page": 1,
        "sort_by": "popularity.desc"
    }
    
    # Add genre filter
    if filters.get('genres'):
        all_genres = get_genre_list()
        genre_map = {g['name'].lower(): g['id'] for g in all_genres}
        genre_ids = []
        for genre_name in filters['genres']:
            if genre_name.lower() in genre_map:
                genre_ids.append(str(genre_map[genre_name.lower()]))
        if genre_ids:
            params["with_genres"] = ",".join(genre_ids)
    
    # Add actor filter
    if filters.get('actor'):
        person_id = search_person_id(filters['actor'])
        if person_id:
            params["with_cast"] = person_id
    
    # Add rating filter
    if filters.get('rating_min'):
        params["vote_average.gte"] = float(filters['rating_min'])
    if filters.get('rating_max'):
        params["vote_average.lte"] = float(filters['rating_max'])
    
    # Add year filter
    if filters.get('year'):
        params["primary_release_year"] = int(filters['year'])
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return data.get("results", [])
    except:
        return []


# ========== HELPER FUNCTIONS FOR ADVANCED SEARCH ==========

def get_genre_list():
    """
    Get list of all TMDB genres with their IDs.
    Returns list of genre dictionaries.
    """
    url = f"{BASE_URL}/genre/movie/list"
    params = {
        "api_key": TMDB_KEY,
        "language": "en-US"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return data.get("genres", [])
    except:
        return []


def search_person_id(person_name):
    """
    Search for a person (actor/director) and return their TMDB ID.
    """
    if not person_name:
        return None
        
    url = f"{BASE_URL}/search/person"
    params = {
        "api_key": TMDB_KEY,
        "query": person_name,
        "language": "en-US",
        "page": 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        results = data.get("results", [])
        if results:
            return results[0]['id']
    except:
        pass
    return None


def search_movies_with_filters(query, filters=None):
    """
    Search movies by title with optional filters.
    
    Args:
        query (str): Movie title to search for
        filters (dict): Optional filters including:
            - genres: List of genre names
            - actor: Actor name
            - rating_min: Minimum rating
            - rating_max: Maximum rating
            - year: Release year
    
    Returns:
        list: A list of movie dicts matching search + filters
    """
    if not query:
        return []
    
    url = f"{BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_KEY,
        "language": "en-US",
        "query": query,
        "page": 1
    }
    
    # Add filters if provided
    if filters:
        # Add genre filter
        if filters.get('genres'):
            all_genres = get_genre_list()
            genre_map = {g['name'].lower(): g['id'] for g in all_genres}
            genre_ids = []
            for genre_name in filters['genres']:
                if genre_name.lower() in genre_map:
                    genre_ids.append(str(genre_map[genre_name.lower()]))
            if genre_ids:
                params["with_genres"] = ",".join(genre_ids)
        
        # Add actor filter
        if filters.get('actor'):
            person_id = search_person_id(filters['actor'])
            if person_id:
                params["with_cast"] = person_id
        
        # Add rating filter
        if filters.get('rating_min'):
            params["vote_average.gte"] = float(filters['rating_min'])
        if filters.get('rating_max'):
            params["vote_average.lte"] = float(filters['rating_max'])
        
        # Add year filter
        if filters.get('year'):
            params["primary_release_year"] = int(filters['year'])
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return data.get("results", [])
    except:
        return []
