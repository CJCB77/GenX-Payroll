import requests
from django.conf import settings

class OdooClientError(Exception):
    pass

class OdooClient:
    def __init__(self):
        self.base_url = settings.ODOO_BASE_URL
    
    def authenticate(self, username, password, database, method="credentials"):
        login_url = f"{self.base_url}/rest/auth"
        try:
            res = requests.post(
                login_url,
                json={
                    "method": method,
                    "username": username,
                    "password": password,
                    "database": database
                },
                timeout=10
            )
            if res.status_code != 200:
                raise OdooClientError("Invalid credentials")
            return res.json()
        except requests.exceptions.RequestException as e:
            raise OdooClientError(f"Connection error: {e}")