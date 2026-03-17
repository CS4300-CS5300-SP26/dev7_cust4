from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.conf import settings
from .models import CarouselImage
from django.contrib.auth.forms import UserCreationForm

def landing_page(request):
    """
    Renders the landing page of the web application.
    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTPResponse: A rendering of the landing.html page.
    """
    return render(request, 'landing.html')


def signup_view(request):
    """
    Handles creating accounts for new users to create bookings.

    Args:
        request (HTTP request): Contains information about the request.

    Returns:
        HTTP Response: Contains the signup form or redirects user to home page if they successfully created an account.
    """
    # If form has been submitted, create the user if form is valid. Using the django UserCreationForm to handle creating accounts.
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("landing")
    # Display form.
    else:
        form = UserCreationForm()

    carousel_imgs = CarouselImage.objects.all()
    return render(request, "signup.html", {"form": form, "carousel_imgs": carousel_imgs})

    
class CustomLoginView(LoginView):
    """
    Changes Django's LoginView to edit the context that is passed to the login page.
    """
    template_name = "registration/login.html"
    redirect_autheticated_user = True

    def get_context_data(self, **kwargs):
        """
        Changes Django's login view and adds the carousel images to the context.

        Returns:
            context (HTTP Response): Contains the login context along with the carousel
                images.
        """
        context = super().get_context_data(**kwargs)
        carousel_imgs = CarouselImage.objects.all()
        context["carousel_imgs"] = carousel_imgs
        return context
    
