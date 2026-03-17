from behave import given, when, then
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.urls import reverse


@given("I have an account with {username} and {password}")
def step_impl(context, username, password):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        user.save()
    context.user = user
    context.username = username
    context.password = password


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
    user, created = User.objects.get_or_create(username="user5678")
    if created:
        user.set_password("password.5678")
        user.save()

    context.test.client.login(username="user5678", password="password.5678")


@given("I click the log out button")
def step_impl(context):
    logout_url = reverse("logout")
    context.response = context.test.client.post(logout_url, follow=True)


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
    context.response = context.test.client.post(
        reverse("login"),
        {
            "username": context.username,
            "password": context.password,
        },
    )


@when("I submit the signup form")
def step_impl(context):
    context.response = context.test.client.post(
        reverse("signup"),
        {
            "username": context.username,
            "password1": context.password,
            "password2": context.confirm_password,
        },
    )


@then("I should be logged in")
def step_impl(context):
    # Check if logged in by verifying authentication
    context.test.assertIn("_auth_user_id", context.test.client.session)


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
