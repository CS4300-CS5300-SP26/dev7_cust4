from home.services import supabase


def supabase_context_processor(request):
    """
    Allows the user's username and email and if they are authenticated to be
    accessed through templates.

    Args:
        request (HTTP request): Contains information about the request.

    Return:
        dict: Contains the user's authentication status, username, and email
            (which are empty if they are not authenticated).
    """
    is_authenticated = supabase.is_authenticated(request)
    username = ""
    email = ""
    if is_authenticated:
        username = request.session.get("supabase_username")
        email = request.session.get("supabase_user_email")

    return {"is_authenticated": is_authenticated, "username": username, "email": email}
