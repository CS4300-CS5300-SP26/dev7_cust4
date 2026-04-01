from django.shortcuts import render, redirect
from django.conf import settings
import requests
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .services.tmdb import fetch_movies, fetch_movie_detail, get_cast, get_director
from .services import supabase
from django.contrib import messages

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

    return render(request, "movie_detail.html", 
    {"movie": movie, "cast": get_cast(movie), "director": get_director(movie),})

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
        HTTP Response: Contains the login form or redirects user if they successfully logged in.
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
        HTTP Response: Contains the login form or redirects user if they successfully logged in.
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
        HTTP Response: Contains the login form or redirects user if they successfully logged in.
    """
    supabase.logout(request)
    return redirect("/")