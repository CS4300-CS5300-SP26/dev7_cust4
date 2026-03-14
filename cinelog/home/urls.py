from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.landing_page, name="landing"),
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', views.signup_view, name='signup'),
]