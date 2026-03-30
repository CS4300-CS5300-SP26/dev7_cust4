import os
from supabase import create_client, Client
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


# Set a max for number of links user can recieve.
MAX_EMAILS_1_HOUR = 4

url: str = settings.SUPABASE_URL
key: str = settings.SUPABASE_KEY
supabase: Client = create_client(url, key)

def supabase_sign_up(request, username, email, password):
    try:
        data = supabase.auth.sign_up({
            'email': email,
            'password': password,
            'options': {
                'data': {
                    "username": username
                }
            }
        })

    except Exception as e:
        messages.error(request, f"Error: {e}")

def supabase_log_in(request, email, password):
    try:
        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        if response.user:
            request.session["supabase_access_token"] = response.session.supabase_access_token
            request.session["supabase_user_email"] = email

        messages.success(request, "Logged in.")
        return True
        
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return False

def is_valid_email(request, email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return False


def send_magic_link_login(request, email):
    """
    Use Supabase and Google SMTP to send magic link to login to user.

    Args:
        email (str): Email submitted in form by user.
    """
    redirect_url = request.build_absolute_uri("/movies/")
    try:
        response = supabase.auth.sign_in_with_otp({
            'email': email,
            'options': {
                'should_create_user': True, # User must have an account.
                'email_redirect_to': redirect_url,
            },
        })

        messages.success(request, f"Link sent to {email}!")
    
    except Exception as e:
        messages.error(request, f"Error: {e}")


def reached_limit_magic_login(email):
    """
    Determine if user has reached limit of emails for magic login.

    Args:
        email (str): Email submitted in form by user.

    Returns:
        boolean: Represents if user has reached login limit.
    """
    cache_key = f"magic_link_accesses{email.lower()}"
    num_requests = cache.get(cache_key, 0)

    if num_requests >= MAX_EMAILS_1_HOUR:
        return True

    cache.set(cache_key, num_requests + 1, timeout=3600)
    return False

def is_authenticated(request):
    return {
        "user_authenticated": "supabase_a"
    }