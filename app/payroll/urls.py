from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    SyncEmployeeHook, 
    SyncContractHook,
    FieldWorkerListView,
    FieldWorkerDetailView,
    FarmViewSet,
)

router = SimpleRouter()
router.register(r"farms", FarmViewSet, basename="farm")

app_name = "payroll"

urlpatterns = [
    path("hooks/employee", SyncEmployeeHook.as_view(), name="hook-employee"),
    path("hooks/contract", SyncContractHook.as_view(), name="hook-contract"),
    path("fieldworkers", FieldWorkerListView.as_view(), name="fieldworker-list"),
    path("fieldworkers/<int:pk>", FieldWorkerDetailView.as_view(), name="fieldworker-detail"),
    path("", include(router.urls)),
]