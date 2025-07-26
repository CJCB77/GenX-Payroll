from rest_framework import authentication, exceptions
from django.contrib.auth import get_user_model
from django.conf import settings
import jwt
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class OdooJWTAuthentication(authentication.BaseAuthentication):
    """
    1) Reads "Authorization: Bearer <token>"
    2) jwt.decode(..., ODOO_JWT_SECRET) to verify signature + exp
    3) get_or_create local User mirror
    """
    keyword = 'Bearer'

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        logger.info(f"Header: {header}")
        if not header or header[0].decode().lower() != self.keyword.lower():
            return None
        
        if len(header) != 2:
            raise exceptions.AuthenticationFailed('Invalid token header')
        
        token = header[1].decode()
        logger.info(f"Token: {token}")
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_aud": False}
            )
            logger.info(f"Payload: {payload}")
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {e}')
        
        # get or create local user
        user, _ = User.objects.get_or_create(
            username=payload['username'], 
            odoo_user_id=payload['sub'],
            defaults={
                "first_name": payload.get("name",'').split()[0],
                "last_name": payload.get("name",'').split()[1],
                "email": payload.get("email", '')
            }
        )
        logger.info(f"User: {user}")
        
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User is inactive')
        
        return (user, token)