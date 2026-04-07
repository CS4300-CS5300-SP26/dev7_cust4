from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name="landing"),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('magiclogin/', views.magic_login, name='magic_login'),
    path('callback/', views.magic_callback, name='callback'),
    path('logout/', views.logout_view, name='logout'),
    path('movies/', views.movies_view, name='movies'),
    path('movies/<int:movie_id>/', views.movie_detail_view, name='movie_detail'),
    path('movies/add-watchlist/<int:movie_id>/', views.add_to_watchlist, name="add_to_watchlist"),
    path('movies/remove-watchlist/<int:movie_id>/', views.remove_from_watchlist, name="remove_from_watchlist"),
    path('watchlist/', views.watchlist_view, name='watchlist'),
    path('movies/hidden/', views.hidden_movies_view, name='hidden_movies'),
    path('movies/hide/<int:movie_id>/', views.hide_movie, name='hide_movie'),
    path('movies/unhide/<int:movie_id>/', views.unhide_movie, name='unhide_movie'),
]