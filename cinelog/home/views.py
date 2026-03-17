from django.shortcuts import render, redirect
from django.conf import settings
import requests
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from .models import CarouselImage
from django.contrib.auth.forms import UserCreationForm

TMDB_API_KEY = settings.TMDB_API_KEY
OMDB_API_KEY = settings.OMDB_API_KEY

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

    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    movies = response.json().get("results", [])

    return render(request, "movies.html", {"movies": movies})

def movie_detail_view(request, movie_id):

    # fetch full movie details by ID
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,videos"
    response = requests.get(url)
    movie = response.json()

    runtime = movie.get("runtime", 0)
    hours = runtime // 60
    minutes = runtime % 60
    formatted_runtime = f"{hours}h {minutes}m"

    return render(request, "movie_detail.html", {"movie": movie, "runtime": formatted_runtime})
def signup_view(request):
    """
    Handles creating accounts for new users to create bookings.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTP Response: Contains the signup form or redirects user to home page if they successfully created an account.
    """
    # If form has been submitted, create the user if form is valid. Using the django UserCreationForm to handle creating accounts.
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("landing")
    # Display form.
    else:
        form = UserCreationForm()

    carousel_imgs = CarouselImage.objects.all()
    return render(request, "signup.html", {"form": form, "carousel_imgs": carousel_imgs})

    
class CustomLoginView(LoginView):
    """
    Changes Django's LoginView to edit the context that is passed to the login page.
    """
    template_name = "registration/login.html"
    redirect_autheticated_user = True

    def get_context_data(self, **kwargs):
        """
        Changes Django's login view and adds the carousel images to the context.

        Returns:
            context (HTTP Response): Contains the login context along with the carousel
                images.
        """
        context = super().get_context_data(**kwargs)
        carousel_imgs = CarouselImage.objects.all()
        context["carousel_imgs"] = carousel_imgs
        return context
    
