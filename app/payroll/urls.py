from django.urls import path
from .views import SyncEmployeeHook, SyncContractHook

app_name = "payroll"

urlpatterns = [
    path("hooks/employee", SyncEmployeeHook.as_view(), name="hook-employee"),
    path("hooks/contract", SyncContractHook.as_view(), name="hook-contract"),
]