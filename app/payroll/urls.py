from django.urls import path, include
from rest_framework_nested.routers import SimpleRouter, NestedSimpleRouter
from .views import (
    SyncEmployeeHook, 
    SyncContractHook,
    FieldWorkerListView,
    FieldWorkerDetailView,
    FarmViewSet,
    ActivityGroupSet,
    ActivitySet,
    UomViewSet,
    LaborTypeViewSet,
    TariffViewSet,
    PayrollBatchViewSet,
    PayrollConfigurationView,
    PayrollBatchLineViewSet,
)

router = SimpleRouter(trailing_slash=False)
router.register(r"farms", FarmViewSet, basename="farm")
router.register(r"activity-groups", ActivityGroupSet, basename="activity-group")
router.register(r"activities", ActivitySet, basename="activity")
router.register(r"uoms", UomViewSet, basename="uom")
router.register(r"labor-types", LaborTypeViewSet, basename="labor-type")
router.register(r"tariffs", TariffViewSet, basename="tariff")
router.register(r"payroll-batches", PayrollBatchViewSet, basename="payroll-batch")

# Nested
batch_router = NestedSimpleRouter(router, r"payroll-batches", lookup="batch")
batch_router.register(r"payroll-lines", PayrollBatchLineViewSet, basename="payroll-line")

app_name = "payroll"

urlpatterns = [
    path("hooks/employee", SyncEmployeeHook.as_view(), name="hook-employee"),
    path("hooks/contract", SyncContractHook.as_view(), name="hook-contract"),
    path("fieldworkers", FieldWorkerListView.as_view(), name="fieldworker-list"),
    path("fieldworkers/<int:pk>", FieldWorkerDetailView.as_view(), name="fieldworker-detail"),
    path("configuration", PayrollConfigurationView.as_view(), name="configuration"),
    path("", include(router.urls)),
    path("", include(batch_router.urls)),
]