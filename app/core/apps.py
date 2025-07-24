from django.apps import AppConfig
from app.scheme import OdooJWTAuthenticationScheme


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
