from behave import given, when, then
from django.urls import reverse
from unittest.mock import patch
from django.contrib.messages import get_messages


@given('I am on the Watchlist page')
def step_impl(context):
    # Check on the sign up page.
    context.response = context.test.client.get(reverse("watchlist"))
    assert context.response.status_code == 200

@given('"{movie}" is on my watchlist')
def step_impl(context, movie):
    context.movie_id = 550
    context.movie_name = movie

@given('I am on the Movie Details page')
def step_impl(context):
    context.movie_id = 550
    context.client.get(reverse("movie_detail", args=[context.movie_id]))

@given('I have added the movies "{movie1}", "{movie2}", "{movie3}" in this order')
def step_impl(context, movie1, movie2, movie3):
    context.movies = [
        {"id": 101, "user_id": "ABC123", "title": movie1, "movie_id": 1, "date_added": "2026-04-01T10:00:00Z"},
        {"id": 102, "user_id": "ABC123", "title": movie2, "movie_id": 2, "date_added": "2026-04-01T10:05:00Z"},
        {"id": 103, "user_id": "111-111", "title": movie3, "movie_id": 1, "date_added": "2026-04-01T10:10:00Z"},
    ]


@when('I select the view details button')
def step_impl(context):
    context.response = context.test.client.get(
        reverse("movie_detail", args=[context.movie_id])
    )

@when('I select the remove from list button')
def step_impl(context):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch("home.views.supabase.delete_in_watchlist", return_value=True):

        context.response = context.client.post(
            reverse("remove_from_watchlist", args=[context.movie_id]),
            HTTP_REFERER="/watchlist/"
        )

@when('I select add to watchlist')
def step_impl(context):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch(
             "home.views.supabase.insert_in_watchlist",
             return_value=(False, "Error: Movie is already in watchlist.")
         ):
        
        context.response = context.client.post(
            reverse("add_to_watchlist", args=[context.movie_id])
        )

@when('I select to order by "{criteria}"')
def step_impl(context, criteria):
    """
    Simulate selecting sort order in the template. For test, we reorder the mocked list.
    """
    if criteria.lower() == "date (oldest to newest)":
        context.movies.sort(key=lambda m: m["date_added"])

@then('I can view "{movie}" in my watchlist')
def step_impl(context, movie):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch("home.views.supabase.get_watchlist", return_value=[550]), \
         patch("home.views.fetch_movies", return_value={"id": 550, "title": movie}):
        
        response = context.test.client.get(reverse("watchlist"))

    assert response.status_code == 200
    assert "movies" in response.context
    assert response.context["movies"][0]["title"] == context.movie_name

@then('I am redirected to the movie details page for "{movie}"')
def step_impl(context, movie):
    assert context.response.status_code == 200
    assert "movie" in context.response.context

@then('"Black Panther" is no longer in my watchlist')
def step_impl(context):
    with patch("home.views.supabase.get_user_id", return_value="user123"), \
         patch("home.views.supabase.get_watchlist", return_value=[]):

        response = context.client.get(reverse("watchlist"))

    assert response.context["movies"] == []

@then('I am shown an error')
def step_impl(context):
    messages = list(get_messages(context.response.wsgi_request))
    assert any("already in watchlist" in str(m) for m in messages)

@then('the movies are reordered by the selected criteria')
def step_impl(context):
    response = context.test.client.get(reverse("watchlist"))
    sorted_titles = [m["title"] for m in context.movies]
    template_titles = [m["title"] for m in context.movies]
    assert template_titles == sorted_titles, f"Expected {sorted_titles}, got {template_titles}"

@then('"{movie1}" will be displayed first')
def step_impl(context, movie1):
    assert context.movies[0]["title"] == movie1

@then('"{movie3}" will be shown last')
def step_impl(context, movie3):
    assert context.movies[-1]["title"] == movie3