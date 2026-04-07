from django.shortcuts import render, redirect
from django.conf import settings
import requests
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .services.tmdb import fetch_movies, fetch_movie_detail, get_cast, get_director, search_movies
from .services import supabase
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Movie
from django.urls import reverse


def landing_page(request):
    """
    Renders the landing page of the web application.
    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTPResponse: A rendering of the landing.html page.
    """
    return render(request, 'landing.html')

# anyone can see this (no login required)
def movies_view(request):
    """
    Render the movies page with separate TMDB categories.
    Hidden movies are filtered out for logged-in users.
    """
    user_id = supabase.get_user_id(request)
    hidden_ids = set(supabase.get_hidden_movies(user_id)) if user_id else set()

    popular = [m for m in fetch_movies("popular") if m.get("id") not in hidden_ids]
    top_rated = [m for m in fetch_movies("top_rated") if m.get("id") not in hidden_ids]
    now_playing = [m for m in fetch_movies("now_playing") if m.get("id") not in hidden_ids]

    return render(request, "movies.html", {
        "movies": popular,
        "top_rated_movies": top_rated,
        "now_playing_movies": now_playing,
    })

def movie_detail_view(request, movie_id):
    """
    Render the detail page for a single movie.
    """
    movie = fetch_movie_detail(movie_id)

    # convert runtime to hours&mins for better readability
    runtime = movie.get("runtime")
    if runtime:
        hours = runtime // 60
        minutes = runtime % 60
        movie["formatted_runtime"] = f"{hours}h {minutes}m"
    else:
        movie["formatted_runtime"] = "N/A"

    user_id = supabase.get_user_id(request)

    # Add to response if movie is already in watchlist.
    if user_id and supabase.get_watchlist(user_id, movie_id=movie_id):
        in_watchlist = True
    else:
        in_watchlist = False

    is_hidden = bool(supabase.get_hidden_movies(user_id, movie_id=movie_id)) if user_id else False

    return render(request, "movie_detail.html",
    {"movie": movie, "cast": get_cast(movie), "director": get_director(movie), "in_watchlist": in_watchlist, "is_hidden": is_hidden})

def signup_view(request):
    """
    Handles creating accounts for new users.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTP Response: Contains the signup form or redirects user to home page if they successfully created an account.
    """
    # If form has been submitted, create the user if form is valid. Using the django UserCreationForm to handle creating accounts.
    if request.method == "POST":
        # Get the email and username from the form.
        email = request.POST.get("email")
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
    
        form = UserCreationForm(request.POST)
        
        # Check if email is a valid email.
        if not supabase.is_valid_email(request, email):
            return redirect("signup")
        
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("signup")

        # User Django to validate other fields and ensure they meet requirements.
        if form.is_valid():
            password = request.POST.get("password1")
            if not supabase.supabase_sign_up(request, username, email, password):
                return redirect("signup") 
            return redirect("movies")

    # Display form.
    else:
        form = UserCreationForm()

    return render(request, "signup.html", {"form": form, "movies": fetch_movies("popular")})

def login_view(request):
    """
    Handles logging a user into their account through supabase.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTP Response: Contains the login form or redirects user to movies page if they successfully logged in.
    """
    # If form has been submitted, create the user if form is valid. Using the django UserCreationForm to handle creating accounts.
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not supabase.is_valid_email(request, email):
            return redirect("login")
        
        if not email or not password:
            messages.error(request, "Please enter fill in each field.")
            return redirect("login")
        
        if supabase.supabase_log_in(request, email, password):
            return redirect("movies")

    return render(request, "login.html", {"movies": fetch_movies("popular")})


def magic_login(request):
    """
    Renders magic login page and handles logging user in through a magic link.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTPResponse: Contains the login form or redirects user if they successfully logged in (or redirects user).
    """
    # If form has been submitted, create the user if form is valid.
    if request.method == "POST":
        email = request.POST.get("email")

        if supabase.reached_limit_magic_login(email):
            messages.error(request, "Reached max limit of magic logins for the hour. Try later or login with password.")
            return redirect("magic_login")

        # User must enter an email. If not, display error.
        if not email:
            messages.error(request, "Please enter your email.")
            return redirect("magic_login")

        # Use supabase to send magic link in email.
        supabase.send_magic_link_login(request, email)
        return redirect("magic_login")

    return render(request, "magic_link_login.html", {"movies": fetch_movies("popular")})


def magic_callback(request):
    """
    Redirects user after they have been authenticated or not by the magic link.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTPResponseRedirect: Redirects user to login page if unsuccesful, movies page if successful.
    """
    if supabase.get_user_magic_link(request):
        return redirect("movies")
    return redirect("magic_login")


def logout_view(request):
    """
    Logs the user out of supabase and redirects them.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTPResponseRedirect: Redirects user to home page.
    """
    supabase.logout(request)
    return redirect("/")


def add_to_watchlist(request, movie_id):
    """
    Adds a movie to the user's watchlist in database.
    Args:
        request (HTTP request): Contains information about the request.
        movie_id (int): Value representing movie in TMDB (passed in url).

    Returns:
        HTTPResponseRedirect: Redirects to current page (movie_detail page).
    """
    if request.method == "POST":
        user_id = supabase.get_user_id(request)
        if not user_id:
            messages.error(request, "Must be logged in to add movie to watchlist.")
            return redirect("login")
        
        # Insert movie into watchlist table in database.
        success, message = supabase.insert_in_watchlist(user_id, movie_id)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect("movie_detail", movie_id=movie_id)

def remove_from_watchlist(request, movie_id):
    """
    Remove a movie from the user's watchlist in database.

    Args:
        request (HTTP request): Contains information about the request.
        movie_id (int): Value representing movie in TMDB (passed in url).

    Returns:
        HTTPResponseRedirect: Redirects to referring page or login page if not signed in.
    """
    if request.method == "POST":
        user_id = supabase.get_user_id(request)
        if not user_id:
            messages.error(request, "Must be logged in to remove movie from watchlist.")
            return redirect("login")
        
        # Remove movie into watchlist table in database.
        success = supabase.delete_in_watchlist(user_id, movie_id)
        if not success:
            messages.error(request, "Unable to remove movie. Please try again.")
        
        return redirect(request.META.get("HTTP_REFERER", f"/movies/{movie_id}/"))

def watchlist_view(request):
    """
    Renders the watchlist page of the web application.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTPResponse: A rendering of the watchlist.html page.
    """
    user_id = supabase.get_user_id(request)
    sort = request.GET.get("sort", "")
    if not user_id:
        return render(request, 'watchlist.html')

    movie_ids = supabase.get_watchlist(user_id)
    if "date" in sort:
        movie_ids = sort_movies_date(user_id, sort)

    movies = []
    for movie in movie_ids:
        movie = fetch_movies(movie, single=True)
        if movie.get("id"):
            movies.append(movie)
    
    if "title" in sort:
        movies = sort_movies_title(movies, sort)

    return render(request, 'watchlist.html', {"movies": movies})

def sort_movies_title(movies, sort_method):
    """
    Given movies list, sorts them based on their title.

    Args:
        movies (list): Contains dictionaries with information about movies in user's watchlist.
        sort_method (str): Contains how movies should be sorted.

    Returns:
        list: Sorted version of passed in movies.
    """
    if sort_method == "ascending_title":
        movies.sort(key=lambda x: x.get("title", "").lower())

    elif sort_method == "descending_title":
        movies.sort(key=lambda x: x.get("title", "").lower(), reverse=True)
    return movies

def sort_movies_date(user_id, sort_method):
    """
    Given movies ids, accesses supabase to find when movies were added and sort them by date.

    Args:
        user_id (str): Unique id that can be used to reference a user.
        sort_method (str): Contains how movies should be sorted.

    Returns:
        list: Sorted version of passed in movies.
    """
    if sort_method == "ascending_date":
        movie_ids = supabase.get_watchlist(user_id, order=True, descending=False)

    elif sort_method == "descending_date":
        movie_ids = supabase.get_watchlist(user_id, order=True, descending=True)

    return movie_ids

def library_view(request):
    """
    Renders the My Library page, displaying all movies the user
    has logged with their personal ratings, notes, and watch preferences.
    """
    user_id = supabase.get_user_id(request)
    if not user_id:
        return redirect('login')

    # each user only sees their OWN movies
    movies = Movie.objects.filter(user=request.user)

    # Get search query (general input)
    query = request.GET.get("q", "").strip()
    search_results = []

    # Only search if user typed something
    if query:
        search_results = search_movies(query)

    return render(request, "library.html", {
        "movies": movies,
        "search_results": search_results,
    })
    
def add_movie_view(request):
    user_id = supabase.get_user_id(request)
    if not user_id:
        return redirect('login')

    if request.method == "POST":
        title   = request.POST.get("title", "").strip()
        poster  = request.POST.get("poster", "").strip()
        tmdb_id = request.POST.get("tmdb_id", "").strip()
        rating  = request.POST.get("rating", 3)
        notes   = request.POST.get("notes", "").strip()

        if not tmdb_id:
            messages.error(request, "Invalid movie selection.")
            return redirect("library")

        # duplicate check to this user only
        movie, created = Movie.objects.get_or_create(
            user=request.user,
            tmdb_id=tmdb_id,
            defaults={
                "title":      title,
                "poster_url": poster,
                "rating":     rating,
                "notes":      notes,
            }
        )

        if created:
            messages.success(request, f'"{title}" added to your library!')
        else:
            messages.warning(request, f'"{title}" is already in your library.')

    return redirect("library")

def edit_movie_view(request):
    """
    Update the rating and notes for a movie already in user's library.

    Args: 
    request: POST request containing movie_id, rating, and notes.

    Returns: Redirect user back to library page after saving changes.
    """

    user_id = supabase.get_user_id(request)
    if not user_id:
        return redirect('login')

    if request.method == "POST":
        movie_id = request.POST.get("movie_id")
        rating   = request.POST.get("rating", 3)
        notes    = request.POST.get("notes", "").strip()

        movie = Movie.objects.filter(id=movie_id, user=request.user).first()
        if movie:
            movie.rating = rating
            movie.notes  = notes
            movie.save()
            messages.success(request, f'"{movie.title}" updated.')
        else:
            messages.error(request, "Movie not found.")

    return redirect("library")

def remove_movie_view(request, movie_id):
    """
    Delete a movie from the user's library.
    """

    user_id = supabase.get_user_id(request)
    if not user_id:
        return redirect('login')

    if request.method == "POST":
        movie = Movie.objects.filter(id=movie_id, user=request.user).first()
        if movie:
            movie.delete()
            messages.success(request, f'"{movie.title}" removed from your library.')
        else:
            messages.error(request, "Movie not found.")

    return redirect("library")

def hide_movie(request, movie_id):
    """
    Hides a movie from the user's browsing experience.

    Args:
        request (HTTP request): Contains information about the request.
        movie_id (int): Value representing movie in TMDB (passed in url).

    Returns:
        HTTPResponseRedirect: Redirects to referring page or login if not signed in.
    """
    if request.method == "POST":
        user_id = supabase.get_user_id(request)
        if not user_id:
            messages.error(request, "Must be logged in to hide a movie.")
            return redirect("login")

        success, message = supabase.insert_hidden_movie(user_id, movie_id)
        if success:
            messages.success(request, f'Movie hidden. <a href="/movies/unhide/{movie_id}/" id="undo-hide" style="text-decoration:underline;" onclick="document.getElementById(\'undo-form-{movie_id}\').submit(); return false;">Undo</a>')
        else:
            messages.error(request, message)

        return redirect("movie_detail", movie_id=movie_id)


def unhide_movie(request, movie_id):
    """
    Restores a hidden movie back to the user's browsing experience.

    Args:
        request (HTTP request): Contains information about the request.
        movie_id (int): Value representing movie in TMDB (passed in url).

    Returns:
        HTTPResponseRedirect: Redirects to referring page or login if not signed in.
    """
    if request.method == "POST":
        user_id = supabase.get_user_id(request)
        if not user_id:
            messages.error(request, "Must be logged in to unhide a movie.")
            return redirect("login")

        success = supabase.delete_hidden_movie(user_id, movie_id)
        if success:
            messages.success(request, "Movie restored to your feed.")
        else:
            messages.error(request, "Unable to unhide movie. Please try again.")

        return redirect(request.META.get("HTTP_REFERER", "/movies/"))


def hidden_movies_view(request):
    """
    Renders a page showing all movies the user has hidden.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTPResponse: A rendering of the hidden_movies.html page.
    """
    user_id = supabase.get_user_id(request)
    if not user_id:
        return render(request, "hidden_movies.html")

    hidden_ids = supabase.get_hidden_movies(user_id)
    movies = []
    for mid in hidden_ids:
        movie = fetch_movies(mid, single=True)
        if movie.get("id"):
            movies.append(movie)

    return render(request, "hidden_movies.html", {"movies": movies})

def search_movies_view(request):
    """
    Search for movies with TMDB search API
    """

    query = request.GET.get('q', '').strip()
    
    if not query:
        # If no query, just show the search page with no results
        return render(request, 'search_results.html', {
            'movies': [],
            'search_query': '',
            'is_search': True
        })
    
    # Search for movies
    search_results = search_movies(query)
    
    return render(request, 'search_results.html', {
        'movies': search_results,
        'search_query': query,
        'is_search': True,
        'result_count': len(search_results)
    })
