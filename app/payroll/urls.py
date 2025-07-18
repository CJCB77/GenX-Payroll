from django.urls import path
from .views import SyncEmployeeHook

app_name = "payroll"

urlpatterns = [
    path("hooks/employee", SyncEmployeeHook.as_view(), name="hook-employee"),
]