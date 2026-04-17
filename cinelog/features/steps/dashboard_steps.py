from behave import given, when, then
from django.urls import reverse
from unittest.mock import patch

TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

@given('I am on the dashboard page')
def step_impl(context):
    with patch("home.views.supabase.get_user_id", return_value=TEST_USER_ID), \
        patch("home.views.supabase.get_hidden_movies", return_value=[]), \
        patch("home.views.fetch_movies", return_value={"id": 1}), \
        patch("home.views.user_statistics.get_genre_statistics", return_value=("Action", [])), \
        patch("home.views.user_statistics.get_size_of_watchlist", return_value=5), \
        patch("home.views.user_statistics.get_size_of_library", return_value=10), \
        patch("home.views.user_statistics.get_num_hours_in_library", return_value="15h 30m"), \
        patch("home.views.user_statistics.get_average_rating", return_value=8.2), \
        patch("home.views.user_statistics.get_monthly_logged_movies", return_value=[]), \
        patch("home.views.user_statistics.get_library_months_for_year", return_value=[1]*12), \
        patch("home.views.user_statistics.get_logged_monthly_average", return_value=2), \
        patch("home.views.user_statistics.get_days_logged", return_value=7):
        context.response = context.test.client.get(reverse("account"))

    assert context.response.status_code == 200

@when('I add a new movie to my watchlist')
def step_impl(context):
    context.initial_count = 5

    with patch("home.views.supabase.get_user_id", return_value=TEST_USER_ID), \
        patch("home.views.supabase.insert_in_watchlist", return_value=(True, "Success")):
        context.test.client.post(
            reverse("add_to_watchlist", args=[999])
        )

@then('I should see statistics about my movies')
def step_impl(context):
    context = context.response.context
    assert "num_in_watchlist" in context
    assert "num_in_library" in context
    assert "total_hours" in context
    assert "average_rating" in context
    assert "top_genre" in context

@then('I should see a statistic for movies logged')
def step_impl(context):
    assert context.response.context["num_in_library"] == 10

@then('a statistic for total hours logged')
def step_impl(context):
    assert context.response.context["total_hours"] == "15h 30m"

@then('a statistic for average rating')
def step_impl(context):
    assert context.response.context["average_rating"] == 8.2

@then('a statistic for most watched genre')
def step_impl(context):
    assert context.response.context["top_genre"] == "Action"

@then('I should see a the total watchlist movie count increase by 1')
def step_impl(context):
    with patch("home.views.supabase.get_user_id", return_value=TEST_USER_ID), \
        patch("home.views.supabase.get_hidden_movies", return_value=[]), \
        patch("home.views.fetch_movies", return_value={"id": 1}), \
        patch("home.views.user_statistics.get_genre_statistics", return_value=("Action", [])), \
        patch("home.views.user_statistics.get_size_of_watchlist", return_value=context.initial_count + 1), \
        patch("home.views.user_statistics.get_size_of_library", return_value=10), \
        patch("home.views.user_statistics.get_num_hours_in_library", return_value="15h 30m"), \
        patch("home.views.user_statistics.get_average_rating", return_value=8.2), \
        patch("home.views.user_statistics.get_monthly_logged_movies", return_value=[]), \
        patch("home.views.user_statistics.get_library_months_for_year", return_value=[1]*12), \
        patch("home.views.user_statistics.get_logged_monthly_average", return_value=2), \
        patch("home.views.user_statistics.get_days_logged", return_value=7):

        response = context.test.client.get(reverse("account"))

    assert response.context["num_in_watchlist"] == context.initial_count + 1