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
    """
    return render(request, "movies.html", {
        "movies": fetch_movies("popular"),
        "top_rated_movies": fetch_movies("top_rated"),
        "now_playing_movies": fetch_movies("now_playing"),
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

    return render(request, "movie_detail.html", 
    {"movie": movie, "cast": get_cast(movie), "director": get_director(movie), "in_watchlist": in_watchlist})

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



def search_movies_view(request):
    """
    Search for movies with TMDB search API
    """

    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('movies')
    
    # Use the new search_movies function
    search_results = search_movies(query)
    
    return render(request, "movies.html", {
        "movies": search_results,
        "top_rated_movies": [],  #Remains empty when seacrhing
        "now_playing_movies": [],  #Remains empty when seacrhing
        "search_query": query,
        "is_search": True
    })
