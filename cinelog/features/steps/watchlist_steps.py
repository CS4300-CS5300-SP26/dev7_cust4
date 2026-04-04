from behave import given, when, then
from django.urls import reverse
from unittest.mock import patch
from django.contrib.messages import get_messages


@given('I am on the Watchlist page')
def step_impl(context):
    # Check on the sign up page.
    context.response = context.test.client.get(reverse("watchlist"))
    assert context.response.status_code == 200

@given('"Black Panther" is on my watchlist')
def step_movie_exists(context):
    context.movie_id = 550

@given('I am on the Movie Details page')
def step_movie_page(context):
    context.movie_id = 550
    context.client.get(reverse("movie_detail", args=[context.movie_id]))


@when('I select the view details button')
def step_view_details(context):
    context.response = context.test.client.get(
        reverse("movie_detail", args=[context.movie_id])
    )

@when('I select the remove from list button')
def step_remove_movie(context):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch("home.views.supabase.delete_in_watchlist", return_value=True):

        context.response = context.client.post(
            reverse("remove_from_watchlist", args=[context.movie_id]),
            HTTP_REFERER="/watchlist/"
        )

@when('I select add to watchlist')
def step_add_watchlist(context):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch(
             "home.views.supabase.insert_in_watchlist",
             return_value=(False, "Error: Movie is already in watchlist.")
         ):
        
        context.response = context.client.post(
            reverse("add_to_watchlist", args=[context.movie_id])
        )

@then('I can view the movies in my watchlist')
def step_view_watchlist(context):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch("home.views.supabase.get_watchlist", return_value=[550]), \
         patch("home.views.fetch_movies", return_value={"id": 550, "title": "Black Panther"}):
        
        response = context.test.client.get(reverse("watchlist"))

    assert response.status_code == 200
    assert "movies" in response.context
    assert response.context["movies"][0]["title"] == "Black Panther"

@then('I am redirected to the movie details page for "Black Panther"')
def step_check_detail(context):
    assert context.response.status_code == 200
    assert "movie" in context.response.context

@then('"Black Panther" is no longer in my watchlist')
def step_confirm_removed(context):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch("home.views.supabase.get_watchlist", return_value=[]):

        response = context.client.get(reverse("watchlist"))

    assert response.context["movies"] == []

@then('I am shown an error')
def step_error_message(context):
    messages = list(get_messages(context.response.wsgi_request))
    assert any("already in watchlist" in str(m) for m in messages)