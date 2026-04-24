# pylint: disable=missing-module-docstring,missing-function-docstring,function-redefined,not-callable
from behave import given, when, then
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from django.http import HttpResponseRedirect
from home.services import supabase
from django.test import Client


@given('I have an account with "{email}", "{username}", and "{password}"')
def step_impl(context, email, username, password):
    session = context.test.client.session
    session["access_token"] = "fake-token"
    session["supabase_user_id"] = "user123"
    session["supabase_user_email"] = email
    session["supabase_username"] = username
    session.save()


@given('I am on the "Sign up" page')
def step_impl(context):
    # Check on the sign up page.
    context.response = context.test.client.get(reverse("signup"))
    assert context.response.status_code == 200


@given('I am on the "Log in" page')
def step_impl(context):
    # Check on the log in page.
    context.response = context.test.client.get(reverse("login"))
    assert context.response.status_code == 200


@given("I am logged in")
def step_impl(context):
    session = context.test.client.session
    session["access_token"] = "111111-111111"
    session["supabase_user_email"] = "user5678@email.com"
    session["supabase_username"] = "user5678"
    session.save()


@given("I click the log out button")
def step_impl(context):
    logout_url = reverse("logout")
    context.response = context.test.client.post(logout_url, follow=True)


@when('I fill in the "Email" field with "{email}"')
def step_impl(context, email):
    context.email = email


@when('I fill in the "Username" field with "{username}"')
def step_impl(context, username):
    context.username = username


@when('I fill in the "Password" field with "{password}"')
def step_impl(context, password):
    context.password = password


@when('I fill in the "Confirm Password" field with "{password}"')
def step_impl(context, password):
    context.confirm_password = password


@when(
    'I fill in the "Password" field with the wrong password "{password}" instead of "{wrong_password}"'
)
def step_impl(context, password, wrong_password):
    context.password = wrong_password


@when("I submit the form")
def step_impl(context):
    with patch("home.views.supabase.supabase_log_in", return_value=True) as mock_log_in:

        def fake_log_in(request, email, password):
            request.session["access_token"] = "111111-111111"
            request.session["supabase_user_email"] = context.email
            request.session["supabase_username"] = "user5678"
            return True

        mock_log_in.side_effect = fake_log_in

        context.response = context.test.client.post(
            reverse("login"),
            {
                "email": context.email,
                "password": context.password,
            },
        )
        context.mock_log_in = mock_log_in


@when("I submit the signup form")
def step_impl(context):
    data = {
        "email": context.email,
        "username": context.username,
        "password1": context.password,
        "password2": context.confirm_password,
    }
    with patch("home.views.supabase.supabase_sign_up") as mock_sign_up:

        def fake_sign_up(request, email, username, password):
            session = context.test.client.session
            session["access_token"] = "111111-111111"
            session["supabase_user_email"] = context.email
            session["supabase_username"] = "user5678"
            session.save()
            return HttpResponseRedirect(reverse("movies"))

        mock_sign_up.side_effect = fake_sign_up

        context.response = context.test.client.post(reverse("signup"), data)
        context.mock_sign_up = mock_sign_up


@then("I should be logged in")
def step_impl(context):
    # Check if logged in by verifying authentication
    context.test.assertIn("access_token", context.test.client.session)
    context.test.assertIn("supabase_user_email", context.test.client.session)


@then('I should be on the "movies" page')
def step_impl(context):
    url = reverse("movies")
    # Redirect
    assert context.response.status_code == 302


@then("the form will not be submitted")
def step_impl(context):
    user = context.response.context["user"]
    context.test.assertFalse(user.is_authenticated)
    context.test.assertNotIn("_auth_user_id", context.test.client.session)


@then("I will be logged out")
def step_impl(context):
    user = context.response.context["user"]
    context.test.assertFalse(user.is_authenticated)


@then("redirected to the home page")
def step_impl(context):
    context.test.assertEqual(context.response.status_code, 200)
    context.test.assertEqual(context.response.request["PATH_INFO"], reverse("landing"))
