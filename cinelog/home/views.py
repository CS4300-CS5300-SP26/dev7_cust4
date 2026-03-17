from django.shortcuts import render
from django.conf import settings
import requests
from django.http import HttpResponse

TMDB_API_KEY = settings.TMDB_API_KEY
OMDB_API_KEY = settings.OMDB_API_KEY

def index(request):
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

    return render(request, "movie_detail.html", {"movie": movie})