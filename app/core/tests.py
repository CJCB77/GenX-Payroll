from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from django.urls import reverse
from django.conf import settings

from rest_framework.test import APITestCase
from rest_framework import status
import jwt
import pytz

class AuthenticatedAPITestCase(APITestCase):
    """
    Base TestCase that:
    - patches OdooClient.authenticate to return JWT dummy token
    - patches jwt.decode to return a dummy payload
    - configures self.client with Bearer token
    """
    LOGIN_URL = reverse("user:login")
    AUTH_TARGET = 'user.views.OdooClient.authenticate'

    def setUp(self):
        super().setUp()

        patcher = patch(self.AUTH_TARGET)
        self.mock_authenticate = patcher.start()
        self.addCleanup(patcher.stop)
        test_username = "ci_user"
        # Build a real looking JWT token
        payload = {
            'sub': "42",                     
            'username': test_username,     
            'name': 'Test User',       
            'email': 'ci@example.com',
            'iat': datetime.now(tz=pytz.UTC),
            'exp': datetime.now(tz=pytz.UTC) + timedelta(days=1),
        }
        dummy_token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        self.mock_authenticate.return_value = {"token": dummy_token}

        # Login
        res = self.client.post(self.LOGIN_URL, {
            "username": test_username,
            "password": "ignored"
            }, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Extract and set the bearer token on the client
        token = res.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")