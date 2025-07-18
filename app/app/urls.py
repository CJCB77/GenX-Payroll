from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from core import views

urlpatterns = [
    path("api/health-check/", views.health_check, name="health-check"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/", 
        SpectacularSwaggerView.as_view(url_name="api-schema"), 
        name="api-docs"
    ),
    path("admin/", admin.site.urls),
    path("api/auth/", include("user.urls")),
    path("api/", include("payroll.urls")),
]
