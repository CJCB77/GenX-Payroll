import time
import requests
from django.conf import settings
import jwt
import logging
import json

logger = logging.getLogger(__name__)

class OdooClientError(Exception):
    pass

class OdooClient:
    def __init__(self):
        self.base_url = settings.ODOO_BASE_URL
        # Service account credentials
        self.username = settings.ODOO_SERVICE_USERNAME
        self.password = settings.ODOO_SERVICE_PASSWORD
        self.database = settings.ODOO_DB
        # in-memory cache
        self._token = None
        self._token_expires = 0
        self.session = requests.Session()
    
    def _authenticate(self):
        """
        Call /rest/auth endpoint and cache the token until it expires
        """
        now = time.time()
        if self._token and now < self._token_expires:
            # Still valid
            logger.info("Using cached token")
            return self._token
        
        logger.info("Authenticating with Odoo...")

        url = f"{self.base_url}/rest/auth"
        payload = {
            "method": "credentials",
            "username": self.username,
            "password": self.password,
            "database": self.database
        }
        try:
            res = self.session.post(url, json=payload, timeout=10)
            res.raise_for_status()
        except requests.RequestException as e:
            self._clear_token()
            raise OdooClientError(f"Connection error: {e}")

        data = res.json()
        token = data.get("token", None)
        if not token:
            raise OdooClientError("No token in response")
        # Lets decode the token to get the expiration date
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload["exp"]
            if exp:
                # Convert to timestamp if needed and add safety buffer
                self._token_expires = int(exp) - 60  # 60 seconds safety buffer
            else:
                # Fallback: assume 24 hours with safety buffer
                self._token_expires = now + 86400 - 300  # 5 minutes safety buffer
        except Exception as e:
            logger.warning(f"Could not decode token expiration:{e}")
            # Fallback: assume 1 hour with safety buffer
            self._token_expires = now + 3600
        
        self._token = token
        # Se the header once so future sessions can reuse it
        self.session.headers["Authorization"] = f"Bearer {self._token}"
        return self._token
    
    def _clear_token(self):
        self._token = None
        self._token_expires = 0
        self.session.headers.pop("Authorization", None)

    def get_model_records(self, model, fields, **filters):
        # Ensure we have a valid token
        self._authenticate()

        url = f"{self.base_url}/rest/models/{model}"
        params = {"_fields": ",".join(fields)}

        # Add field filters - convert boolean values to lowercase strings
        for key, value in filters.items():
            if isinstance(value, bool):
                params[key] = str(value).lower()
            else:
                params[key] = value

        logger.info(f"GET {url} with params: {params}")
        try:
            res = self.session.get(url, params=params, timeout=10)
            if res.status_code == 401:
                # Token may have expired, clear it and try again
                self._clear_token()
                self._authenticate()
                res = self.session.get(url, params=params, timeout=10)
            
            if res.status_code != 200:
                raise OdooClientError(f"GET {url} returned {res.status_code}")
            
            return res.json()
        
        except requests.RequestException as e:
            raise OdooClientError(f"Connection error: {e}")