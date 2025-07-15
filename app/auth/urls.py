from django.urls import path
from .views import LoginView

url_patterns = [
    path("login/", LoginView.as_view(), name="login"),
]