from drf_spectacular.extensions import OpenApiAuthenticationExtension

class OdooJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "user.authentication.OdooJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "name": "BearerAuth",
        }