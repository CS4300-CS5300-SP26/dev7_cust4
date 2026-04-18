from home.services import supabase


def supabase_context_processor(request):
    is_authenticated = supabase.is_authenticated(request)
    username = ""
    email = ""
    if is_authenticated:
        username = request.session.get("supabase_username")
        email = request.session.get("supabase_user_email")

    return {
        "is_authenticated": is_authenticated,
        "username": username,
        "email": email
    }
