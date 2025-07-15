from django.utils import timezone
from rest_framework.response import Response
from rest_framework  import status, generics
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model

from .serializers import LoginSerializer
from .services import OdooClient, OdooClientError
import jwt



User = get_user_model()

def parse_name(full_name):
    """
    Splits a full name into first and last names

    :param str full_name: The full name to split
    :return: A tuple of (first_name, last_name)
    """
    if not full_name:
        return '', ''
    parts = full_name.split()
    if len(parts) >= 2:
        return parts[0], ' '.join(parts[1:])
    return parts[0] if parts else '', ''

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = OdooClient().authenticate(
                serializer.validated_data["username"], 
                serializer.validated_data["password"]
            )
        except OdooClientError:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get or create local user
        token = data["token"]
        # Decode token without verifying, we can trust Odoo
        payload = jwt.decode(token, options={"verify_signature": False})
        username = serializer.validated_data["username"]
        odoo_user_id = payload["sub"]
        first_name, last_name = parse_name(payload.get("name", ''))
        email = payload.get("email", '')

        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "odoo_user_id": odoo_user_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "last_login": timezone.now()
            }
        )
        return Response({"token": token}, status=status.HTTP_200_OK)