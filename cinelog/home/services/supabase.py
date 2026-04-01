import os
from supabase import create_client, Client
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from unittest.mock import MagicMock

# Set a max for number of links user can recieve.
MAX_EMAILS_1_HOUR = 4

def get_supabase_client():
    """
    Creates a supabase client. 

    Returns:
        Client: The supabase client that can be used to access Supabase.
    """
    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_KEY

    if not url or not key:
        supabase_client = MagicMock()

    else:
        supabase_client = create_client(url, key)
    
    return supabase_client

# Create the client.
supabase_client = get_supabase_client()

def create_session(request, response, email, access_token):
    """
    Save information about the user to the session to be used.

    Args:
        request (HTTP request): Contains information about the request.
        response (Response Object): Contains information returned by Supabase.
        email (str): Email submitted in form by user.
    """
    request.session["access_token"] = access_token
    request.session["supabase_user_email"] = email
    request.session["supabase_username"] = response.user.user_metadata.get("username")

def supabase_sign_up(request, username, email, password):
    """
    Sign the user up through Supabase.

    Args:
        request (HTTP request): Contains information about the request.
        username (str): Username entered by the user.
        email (str): Email entered by the user.
        password (str): Password entered by the user.
    
    Returns:
        boolean: Represents if user was sucessfully signed in or not.
    """
    try:
        data = supabase_client.auth.sign_up({
            'email': email,
            'password': password,
            'options': {
                'data': {
                    "username": username
                }
            }
        })
        
        # Log user in too.
        if not supabase_log_in(request, email, password):
            messages.error(request, "Account created. Please login to account.")
        return True

    except Exception as e:
        messages.error(request, f"Error: {e}")
        return False


def supabase_log_in(request, email, password):
    """
    Log the user in through Supabase.

    Args:
        request (HTTP request): Contains information about the request.
        email (str): Email entered by the user.
        password (str): Password entered by the user.

    Returns:
        boolean: Represents if user was logged in or not.
    """
    try:
        response = supabase_client.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        if response.session:
            create_session(request, response, email, response.session.access_token)
        
        return True
        
    except Exception as e:
        messages.error(request, f"Error: {e}")
        return False

def is_valid_email(request, email):
    """
    Uses Django's validation to validate an entered email.

    Args:
        request (HTTP request): Contains information about the request.
        email (str): Email entered by the user.

    Returns:
        boolean: Represents if the entered email is valid or not.
    """
    try:
        validate_email(email)
        return True
    except ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return False

def is_authenticated(request):
    """
    Determines if a user is logged in.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        boolean: Represents if user is logged in or not.
    """
    access_token = request.session.get("access_token")
    
    try:
        user = supabase_client.auth.get_user(access_token)
        return user is not None
    
    except Exception:
        return False

def send_magic_link_login(request, email):
    """
    Use Supabase and Google SMTP to send magic link to login to user.

    Args:
        request (HTTP request): Contains information about the request.
        email (str): Email submitted in form by user.
    """
    redirect_url = request.build_absolute_uri("/callback/")
    try:
        response = supabase_client.auth.sign_in_with_otp({
            'email': email,
            'options': {
                'should_create_user': False, # User must have an account.
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


def get_user_magic_link(request):
    """
    Use the token hash in url from when user clicks magic link to authenticate the user.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        boolean: Represents if token hash sucessfully signed user in.
    """
    # Get the token hash from request.
    token_hash = request.GET.get("token_hash")
    if not token_hash:
        messages.error(request, "Please try again or login with password.")
        return False

    try:
        # Use token hash to authenticate the user.
        response = supabase_client.auth.verify_otp({
            "token_hash": token_hash,
            "type": "email",
        })
        access_token = response.session.access_token
        user = response.user

        if user:
            email = user.email
            # Save user data to session.
            create_session(request, response, email, access_token)
            return True

        else:
            messages.error(request, "Login failed. Please try again or login with password.")
            return False

    except Exception as e:
        messages.error(request, f"Error: {e}")
        return False
            

def logout(request):   
    """
    Log the user out through Supabase.

    Args:
        request (HTTP request): Contains information about the request.
        email (str): Email entered by the user.
        password (str): Password entered by the user.

    Returns:
        boolean: Represents if user was logged in or not.
    """
    access_token = request.session.get("access_token")

    try:
        if access_token:
            supabase_client.auth.sign_out()
    
    except Exception as e:
        messages.error(request, f"Error: {e}")
    
    request.session.flush()
