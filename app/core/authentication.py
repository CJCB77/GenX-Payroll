from rest_framework.authentication import BaseAuthentication
from django.conf import settings


class APIKeyAuthentication(BaseAuthentication):
    """
    Validate that request.headers['X-API-KEY'] == settings.API_KEY
    """

    def authenticate(self, request):
        api_key = request.headers.get("X-API-KEY")
        if not api_key or api_key != settings.API_KEY:
            return None

        return (None, None)