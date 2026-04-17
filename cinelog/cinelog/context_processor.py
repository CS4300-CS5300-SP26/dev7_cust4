from home.services import supabase


def supabase_context_processor(request):
    is_authenticated = supabase.is_authenticated(request)
    username = ""

    if is_authenticated:
        username = request.session.get("supabase_username")

    return {
        "is_authenticated": is_authenticated,
        "username": username,
    }
