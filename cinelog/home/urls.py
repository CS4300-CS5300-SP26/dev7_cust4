"""URL configuration for the Cinelog home app."""
from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path("", views.landing_page, name="landing"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("magiclogin/", views.magic_login, name="magic_login"),
    path("callback/", views.magic_callback, name="callback"),
    path("logout/", views.logout_view, name="logout"),
    path("movies/", views.movies_view, name="movies"),
    path("movies/search/", views.search_movies_view, name="search_movies"),
    path("movies/<int:movie_id>/", views.movie_detail_view, name="movie_detail"),
    path(
        "movies/add-watchlist/<int:movie_id>/",
        views.add_to_watchlist,
        name="add_to_watchlist",
    ),
    path(
        "movies/remove-watchlist/<int:movie_id>/",
        views.remove_from_watchlist,
        name="remove_from_watchlist",
    ),
    path("watchlist/", views.watchlist_view, name="watchlist"),
    path("library/", views.library_view, name="library"),
    path("add-movie/", views.add_movie_view, name="add_movie"),
    path("admin/", admin.site.urls),
    path("library/edit/", views.edit_movie_view, name="edit_movie"),
    path(
        "library/remove/<int:movie_id>/", views.remove_movie_view, name="remove_movie"
    ),
    path("movies/hide/<int:movie_id>/", views.hide_movie, name="hide_movie"),
    path("movies/unhide/<int:movie_id>/", views.unhide_movie, name="unhide_movie"),
    path("account/", views.account_view, name="account"),
    path("account/update_user/", views.update_user_information, name="update_user"),
    path("account/delete_user/", views.delete_user, name="delete_user"),
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/events/', views.calendar_events_api, name='calendar_events'),
    path('movies/<int:movie_id>/where-to-watch/', views.where_to_watch_view, name='where_to_watch'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('recommendations/result/', views.recommendations_result, name='recommendations_result'),
]
