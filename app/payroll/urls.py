from django.urls import path
from .views import (
    SyncEmployeeHook, 
    SyncContractHook,
    FieldWorkerListView,
    FieldWorkerDetailView
)

app_name = "payroll"

urlpatterns = [
    path("hooks/employee", SyncEmployeeHook.as_view(), name="hook-employee"),
    path("hooks/contract", SyncContractHook.as_view(), name="hook-contract"),
    path("fieldworkers", FieldWorkerListView.as_view(), name="fieldworker-list"),
    path("fieldworkers/<int:pk>", FieldWorkerDetailView.as_view(), name="fieldworker-detail"),
]