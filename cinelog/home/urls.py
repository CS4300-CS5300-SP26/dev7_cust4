from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name="landing"),
    path("accounts/", include("django.contrib.auth.urls")),
    # path("signup/", views.signup_html, name="signup"),
    path("movies/", views.movies_view, name="movies"),
    path('movies/<int:movie_id>/', views.movie_detail_view, name='movie_detail'),

]