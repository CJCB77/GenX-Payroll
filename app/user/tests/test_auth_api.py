"""
Tests for user authentication
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from user.services import OdooClientError

User = get_user_model()

LOGIN_URL = reverse("user:login")

class PublicUserEnpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('user.services.OdooClient.authenticate')
    @patch('user.views.jwt')
    def test_login_success_creates_user_and_returns_token(
            self,
            mock_jwt,
            mock_authenticate
        ):
        """
        When our OdooClient.authenticate returns a token and 
        jwt.decode returns a payload, our LoginView should mirror/create
        a user and return a token
        """
        # Prepare a fake payload
        payload = {
            "sub": 123,
            "name": "John Doe",
            "username": "johndoe",
            "email": "john@example.com",
            "exp": 9999999
        }
        mock_jwt.decode.return_value = payload

        # Have my OdooClient.aunthenticate return a token
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        mock_authenticate.return_value = {
            "token": fake_token
        }
        # Fire the POST to my login endpoint
        res = self.client.post(LOGIN_URL, {
            "username": "johndoe",
            "password": "password"
        }, format="json")

        # Assert we get back status 200 and token
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("token", res.data)
        self.assertEqual(res.data["token"], fake_token)

        # Assert that the user row was created
        qs = User.objects.filter(username="johndoe", odoo_user_id=123)
        self.assertTrue(qs.exists(), "User was not created")
        user = qs.get()
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.email, "john@example.com")

    @patch("user.services.OdooClient.authenticate")
    def test_bad_login_credentials(self, mock_authenticate):
        """
        If OdooClien.login raises our OdooClientError, the view
        should return a 401 and not create the user
        """
        mock_authenticate.side_effect = OdooClientError
        res = self.client.post(LOGIN_URL, {
            "username": "johndoe",
            "password": "wrong_password"
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(User.objects.filter(username="johndoe").exists())

    