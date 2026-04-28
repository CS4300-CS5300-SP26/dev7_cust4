import logging
from unittest.mock import MagicMock
from supabase import create_client
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from home.models import Movie

# Set a max for number of links user can recieve.
MAX_EMAILS_1_HOUR = 4


def get_supabase_client():
    """
    Creates a supabase client.

    Returns:
        Client: The supabase client that can be used to access Supabase.
    """
    url = getattr(settings, "SUPABASE_URL", None)
    key = getattr(settings, "SUPABASE_KEY", None)
    if not url or not key:
        client = MagicMock()

    else:
        client = create_client(url, key)

    return client


def get_supabase_admin():
    """
    Creates a supabase admin.

    Returns:
        Client: The supabase client that can be used to access Supabase admin functions.
    """
    url = getattr(settings, "SUPABASE_URL", None)
    key = getattr(settings, "SERVER_KEY", None)

    if not url or not key:
        client = MagicMock()

    else:
        client = create_client(url, key)

    return client


# Create the client.
supabase_client = get_supabase_client()
supabase_admin = get_supabase_admin()


def get_user_supabase_client(access_token, refresh_token):
    """
    Create a Supabase client with an authenticated user session.

    Args:
        access_token (str): Supabase user access token.
        refresh_token (str): Supabase refresh token used to maintain session.

    Returns:
        Client: An authenticated Supabase client instance with the user session set.
    """
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    client.auth.set_session(access_token, refresh_token)
    return client


def create_session(request, response, email, access_token, refresh_token):
    """
    Save information about the user to the session to be used.

    Args:
        request (HTTP request): Contains information about the request.
        response (Response Object): Contains information returned by Supabase.
        email (str): Email submitted in form by user.
    """
    request.session["access_token"] = access_token
    request.session["refresh_token"] = refresh_token
    request.session["supabase_user_email"] = email
    request.session["supabase_username"] = response.user.user_metadata.get("username")
    request.session["supabase_user_id"] = response.user.id


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
        data = supabase_client.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {"data": {"username": username}},
            }
        )

        if not data:
            return False

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
            create_session(
                request,
                response,
                email,
                response.session.access_token,
                response.session.refresh_token,
            )

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
    if not access_token:
        return False

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
        response = supabase_client.auth.sign_in_with_otp(
            {
                "email": email,
                "options": {
                    "should_create_user": False,  # User must have an account.
                    "email_redirect_to": redirect_url,
                },
            }
        )

        if not response:
            messages.error(request, "Error occured.")
            return

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
        response = supabase_client.auth.verify_otp(
            {
                "token_hash": token_hash,
                "type": "email",
            }
        )
        access_token = response.session.access_token
        user = response.user

        if user:
            email = user.email
            # Save user data to session.
            create_session(
                request, response, email, access_token, response.session.refresh_token
            )
            return True

        messages.error(
            request, "Login failed. Please try again or login with password."
        )
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


def get_user_id(request):
    """
    Returns user_id for user to access data in supapabse. None if fails.
    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        str: The user's id (or None if not logged in or request fails).
    """
    if request.session.get("supabase_user_id"):
        return request.session.get("supabase_user_id")

    return None


def insert_in_watchlist(user_id, movie_id):
    """
    Add movie to user's watchlist.

    Args:
        user_id (str): Unique id that can be used to reference a user.
        movie_id (int): Value representing movie in TMDB.

    Returns:
        boolean: Represents if movie was added to watchlist or not.
    """
    try:
        response = (
            supabase_client.table("Watchlist")
            .insert({"user_id": user_id, "movie_id": movie_id})
            .execute()
        )
        if not response:
            return False, "Error occured."

        return True, "Succesfully added movie to watchlist."

    except Exception as e:
        # Display specific error if movie is already in the watchlist.
        if "duplicate key value violates unique constraint" in str(e):
            return False, "Error: Movie is already in watchlist."

        return False, f"Error: {e}"


def delete_in_watchlist(user_id, movie_id):
    """
    Delete a movie from user's watchlist.

    Args:
        user_id (str): Unique id that can be used to reference a user.
        movie_id (int): Value representing movie in TMDB.

    Returns:
        boolean: Represents if movie was removed from watchlist or not.
    """
    try:
        response = (
            supabase_client.table("Watchlist")
            .delete()
            .eq("user_id", user_id)
            .eq("movie_id", movie_id)
            .execute()
        )
        if not response:
            return False

        return True

    except Exception:
        return False


def get_watchlist(user_id, movie_id=None, order=False, descending=False):
    """
    Retrieve a movie from the user's watchlist.

    Args:
        user_id (str): Unique id that can be used to reference a user.
        movie_id (int, optional): If provided, specifies a certain movie to 
            check if is in watchlist.

    Returns:
        list: Contains movie ids of movies in watchlist. Returns empty list if none or if an error.
    """
    try:
        query = supabase_client.table("Watchlist").select("*").eq("user_id", user_id)

        if movie_id is not None:
            query = query.eq("movie_id", movie_id)

        if order:
            query = query.order("date_added", desc=descending)

        response = query.execute()

        # Go through response and retrieve each movie_id
        movie_ids = [row["movie_id"] for row in response.data]
        return movie_ids

    except Exception:
        return []


def insert_hidden_movie(user_id, movie_id):
    """
    Add movie to user's hidden movies list.

    Args:
        user_id (str): Unique id that can be used to reference a user.
        movie_id (int): Value representing movie in TMDB.

    Returns:
        tuple: (bool, str) success flag and message.
    """
    try:
        response = (
            supabase_client.table("HiddenMovies")
            .insert({"user_id": user_id, "movie_id": movie_id})
            .execute()
        )
        if hasattr(response, "error") and response.error:
            error_str = str(response.error)
            if (
                "23505" in error_str
                or "duplicate key value violates unique constraint" in error_str
            ):
                return False, "Movie is already hidden."
            logging.error("insert_hidden_movie supabase error %s:", response.error)
            return False, "An error occurred while hiding the movie."
        return True, "Movie hidden successfully."

    except Exception as e:
        error_str = str(e)
        if (
            "23505" in error_str
            or "duplicate key value violates unique constraint" in error_str
        ):
            return False, "Movie is already hidden."
        logging.error(
            "insert_hidden_movie exception for user %s, movie %s: %s",
            user_id, movie_id, e
        )
        return False, "An error occurred while hiding the movie."


def delete_hidden_movie(user_id, movie_id):
    """
    Remove a movie from user's hidden movies list.

    Args:
        user_id (str): Unique id that can be used to reference a user.
        movie_id (int): Value representing movie in TMDB.

    Returns:
        bool: True if removed successfully, False otherwise.
    """
    try:
        response = (
            supabase_client.table("HiddenMovies")
            .delete()
            .eq("user_id", user_id)
            .eq("movie_id", movie_id)
            .execute()
        )
        if hasattr(response, "error") and response.error:
            logging.error("delete_hidden_movie supabase error: %s", response.error)
            return False
        if response.data:
            return True
        return False

    except Exception as e:
        logging.error(
            "delete_hidden_movie exception for user %s, movie %s: %s",
            user_id, movie_id, e
        )
        return False


def get_hidden_movies(user_id, movie_id=None):
    """
    Retrieve hidden movies for a user.

    Args:
        user_id (str): Unique id that can be used to reference a user.
        movie_id (int, optional): If provided, checks if a specific movie is hidden.

    Returns:
        list: Contains movie_ids of hidden movies. Returns empty list on error.
    """
    try:
        query = supabase_client.table("HiddenMovies").select("*").eq("user_id", user_id)

        if movie_id is not None:
            query = query.eq("movie_id", movie_id)

        response = query.execute()

        if hasattr(response, "error") and response.error:
            logging.error(
                "get_hidden_movies supabase error for user %s: %s",
                user_id, response.error
            )
            return []

        if not response.data:
            return []

        movie_ids = [row["movie_id"] for row in response.data]
        return movie_ids

    except Exception as e:
        logging.error("get_hidden_movies exception for user %s: %s",
            user_id, e
        )
        return []


def change_user_information(new_information, request):
    """
    Change the user's information in supabase.

    Args:
        new_information (dict): Contains the formatted information to send to supabase.
        request (HTTP request): Contains information about the request.

    Returns:
        bool: If the change was successful or not.
    """
    try:
        access_token = request.session.get("access_token")
        refresh_token = request.session.get("refresh_token")

        if not access_token or not refresh_token:
            messages.error(request, "Session expired. Please log in again.")
            return False

        client = get_user_supabase_client(access_token, refresh_token)
        response = client.auth.update_user(new_information)

        if not response:
            return False

        # Update the session's copy of the username if sucessfully updated in supabase.
        if "username" in new_information.get("data", {}):
            request.session["supabase_username"] = new_information["data"]["username"]
        return True

    except Exception as e:
        messages.error(request, e)
        return False


def delete_user_from_supabase(request):
    """
    Delete a user's account from Supabase.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        bool: If the change was successful or not.
    """
    try:
        user_id = request.session.get("supabase_user_id")

        if not user_id:
            return False

        supabase_admin.auth.admin.delete_user(user_id)

        # Remove the information stored in the database.
        Movie.objects.filter(user=user_id).delete()

        # Remove user's information from session.
        request.session.flush()

        return True

    except Exception:
        return False
