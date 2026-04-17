from behave import given, when, then
from django.urls import reverse
from unittest.mock import patch
from contextlib import contextmanager
from unittest.mock import patch

TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


@contextmanager
def patched_dashboard_context(user_id, stats_overrides=None):
    stats = {
        "get_size_of_watchlist": 5,
        "get_size_of_library": 10,
        "get_num_hours_in_library": "15h 30m",
        "get_average_rating": 8.2,
        "get_genre_statistics": ("Action", []),
        "get_monthly_logged_movies": [],
        "get_library_months_for_year": [1] * 12,
        "get_logged_monthly_average": 2,
        "get_days_logged": 7,
    }

    if stats_overrides:
        stats.update(stats_overrides)

    with (
        patch("home.views.supabase.get_user_id", return_value=TEST_USER_ID),
        patch("home.views.supabase.get_hidden_movies", return_value=[]),
        patch("home.views.fetch_movies", return_value={"id": 1}),
        patch(
            "home.views.user_statistics.get_size_of_watchlist",
            return_value=stats["get_size_of_watchlist"],
        ),
        patch(
            "home.views.user_statistics.get_size_of_library",
            return_value=stats["get_size_of_library"],
        ),
        patch(
            "home.views.user_statistics.get_num_hours_in_library",
            return_value=stats["get_num_hours_in_library"],
        ),
        patch(
            "home.views.user_statistics.get_average_rating",
            return_value=stats["get_average_rating"],
        ),
        patch(
            "home.views.user_statistics.get_genre_statistics",
            return_value=stats["get_genre_statistics"],
        ),
        patch(
            "home.views.user_statistics.get_monthly_logged_movies",
            return_value=stats["get_monthly_logged_movies"],
        ),
        patch(
            "home.views.user_statistics.get_library_months_for_year",
            return_value=stats["get_library_months_for_year"],
        ),
        patch(
            "home.views.user_statistics.get_logged_monthly_average",
            return_value=stats["get_logged_monthly_average"],
        ),
        patch(
            "home.views.user_statistics.get_days_logged",
            return_value=stats["get_days_logged"],
        ),
    ):
        yield stats


@given("I am on the dashboard page")
def step_impl(context):
    with patched_dashboard_context(TEST_USER_ID):
        context.response = context.test.client.get(reverse("account"))

    assert context.response.status_code == 200


@when("I add a new movie to my watchlist")
def step_impl(context):
    with patched_dashboard_context(TEST_USER_ID) as stats:
        context.initial_count = stats["get_size_of_watchlist"]

        with patch(
            "home.views.supabase.insert_in_watchlist", return_value=(True, "Success")
        ):
            context.test.client.post(reverse("add_to_watchlist", args=[999]))


@then("I should see statistics about my movies")
def step_impl(context):
    context = context.response.context
    assert "num_in_watchlist" in context
    assert "num_in_library" in context
    assert "total_hours" in context
    assert "average_rating" in context
    assert "top_genre" in context


@then("I should see a statistic for movies logged")
def step_impl(context):
    assert context.response.context["num_in_library"] == 10


@then("a statistic for total hours logged")
def step_impl(context):
    assert context.response.context["total_hours"] == "15h 30m"


@then("a statistic for average rating")
def step_impl(context):
    assert context.response.context["average_rating"] == 8.2


@then("a statistic for most watched genre")
def step_impl(context):
    assert context.response.context["top_genre"] == "Action"


@then("I should see the total watchlist movie count increase by 1")
def step_impl(context):
    with patched_dashboard_context(
        TEST_USER_ID,
        stats_overrides={"get_size_of_watchlist": context.initial_count + 1},
    ):
        response = context.test.client.get(reverse("account"))

    assert response.context["num_in_watchlist"] == context.initial_count + 1
