# pylint: disable=no-member
from collections import defaultdict
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.utils.timezone import now
from django.db.models import Avg
from home.models import Movie
from . import supabase, tmdb


def get_size_of_watchlist(user_id):
    """
    Returns the number of movies in user's the watchlist.

    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        int: Number of movies in watchlist.
    """
    movie_ids = supabase.get_watchlist(user_id)

    num_in_watchlist = len(movie_ids)
    return num_in_watchlist


def get_size_of_library(user_id):
    """
    Returns the number of movies in user's the library.

    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        int: Number of movies in library.
    """
    movies = Movie.objects.filter(user=user_id)

    num_in_library = len(movies)
    return num_in_library


def get_num_hours_in_library(user_id):
    """
    Returns the number of hours of movies in library.
    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        str: Formatted string in h and m for total time in library.
    """
    movies = Movie.objects.filter(user=user_id)
    tot_minutes = 0

    for movie in movies:
        movie_detail = tmdb.fetch_movie_detail(movie.tmdb_id)
        runtime = movie_detail.get("runtime") or 0
        tot_minutes += runtime

    # convert tot_minutes to hours&mins for better readability
    hours = tot_minutes // 60
    minutes = tot_minutes % 60
    return f"{hours}h {minutes}m"


def get_library_months_for_year(user_id):
    """
    Returns the number of movies each added to library for that year.

    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        list: Contains movies added for list for each month of year with index in
            list representing the month.
    """
    months_logged = (
        Movie.objects.filter(user=user_id, created_at__year=now().year)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    months = [0] * 12
    for month in months_logged:
        index = month["month"].month - 1
        months[index] = month["count"]

    return months


def get_monthly_logged_movies(user_id):
    """
    Normalizes data of movies per month to display in a graph.

    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        dict: The value and height for bars in a graph to represent
            the movies for the month.
    """
    months = get_library_months_for_year(user_id)

    # Normalize the data
    if months:
        max_value = max(months)

    else:
        max_value = 1

    monthly_data = []
    for value in months:
        if max_value != 0:
            height = (value / max_value) * 100
        else:
            height = 0

        if value == 0:
            height = 5

        monthly_data.append({"height": height, "value": value})

    return monthly_data


def get_logged_monthly_average(user_id):
    """
    Returns the average number of logged movies per month.
    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        int: Average numbre of logged movies.
    """
    months = get_library_months_for_year(user_id)
    if months:
        return sum(months) // len(months)

    return 0


def get_days_logged(user_id):
    """
    Returns the number of days a user logged a movie.
    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        int: Number of days movies were logged.
    """
    days = Movie.objects.filter(user=user_id).dates("created_at", "day")
    return len(days)


def get_average_rating(user_id):
    """
    Returns the user's average rating for movies in user's library.

    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        float: Average rating of movies.
    """
    result = Movie.objects.filter(user=user_id).aggregate(avg_rating=Avg("rating"))

    return round(result["avg_rating"], 1) if result["avg_rating"] else 0


def get_genre_statistics(user_id):
    """
    Returns information about the top generes for the user.

    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        dict: Contains top 5 generes for user with percentage of movies from that genere.
    """
    movies = Movie.objects.filter(user=user_id)

    genre_values = defaultdict(int)
    for movie in movies:
        # Movie can have several genres.
        genres = tmdb.fetch_movie_detail(movie.tmdb_id).get("genres")

        for genre in genres:
            name_of_genre = genre.get("name")
            if name_of_genre:
                genre_values[name_of_genre] += 1

    if not genre_values:
        return None, []

    total = sum(genre_values.values())

    # Turn dictionary into list of tuples. Only get top 5 genres.
    sorted_genres = sorted(genre_values.items(), key=lambda x: x[1], reverse=True)[:5]
    genre_data = []

    top_five_percent = 0
    for genre in sorted_genres:
        genre_data.append(
            {"genre_name": genre[0], "percent": round((genre[1] / total) * 100)}
        )
        top_five_percent += round((genre[1] / total) * 100)

    other_percent = 0
    if top_five_percent != 100:
        other_percent = max(0, 100 - top_five_percent)

    genre_data.append({"genre_name": "Other", "percent": other_percent})

    return sorted_genres[0][0], genre_data


def get_top_five_movies(user_id):
    """
    Returns information about the top 5 movies for the user.

    Args:
        user_id (UUID): Supabase user id for the user.

    Returns:
        list: Contains movie information for user's top 5 highest rated movies.
    """
    result = Movie.objects.filter(user=user_id).order_by("-rating")[:5]

    movies = []
    for movie in result:
        movie_id = tmdb.fetch_movie_detail(movie.tmdb_id)
        if movie_id:
            movies.append(movie_id)

    return movies
