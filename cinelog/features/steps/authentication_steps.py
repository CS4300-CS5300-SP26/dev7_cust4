from behave import given, when, then
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.urls import reverse


@given("I have an account")
def step_impl(context):
    # Create a user in database
    try:
        user = User.objects.get(username="user5678", password="password.5678")
    except User.DoesNotExist:
        user = User.objects.create_user(username="user5678", password="password.5678")
    context.user = user


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
    user.set_password("password.5678")
    user.save()


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
    user = authenticate(username=context.username, password=context.password)
    assert user is not None


@then('I should be on the "Landing" page')
def step_impl(context):
    url = reverse("landing")
    # Redirect
    assert context.response.status_code == 302
    assert context.response["Location"] == url


@then("the form will not be submitted")
def step_impl(context):
    user = context.response.context["user"]
    context.test.assertFalse(user.is_authenticated)


@then("I will be logged out")
def step_impl(context):
    user = context.response.context["user"]
    context.test.assertFalse(user.is_authenticated)


@then("redirected to the home page")
def step_impl(context):
    context.test.assertEqual(context.response.status_code, 200)
    context.test.assertEqual(context.response.request["PATH_INFO"], reverse("landing"))
