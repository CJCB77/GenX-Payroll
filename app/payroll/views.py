from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, generics
from rest_framework.permissions import AllowAny
from .tasks import sync_employee, sync_contract
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import (
    FieldWorker,
    Farm,    
    ActivityGroup,
    Activity,
    LaborType,
    Uom,
    Tariff,
    PayrollBatch,
    PayrollConfiguration
)
from .serializers import (
    FieldWorkerListSerializer,
    FieldWorkerDetailSerializer,
    FarmSerializer,
    ActivityGroupSerializer,
    ActivitySerializer,
    ActivityDetailSerializer,
    UomSerializer,
    PayrollBatchSerializer,
    PayrollConfigurationSerializer,
    TariffSerializer
)
from .filters import (
    FieldWorkerFilter,
)
from logging import getLogger

logger = getLogger(__name__)


class SyncEmployeeHook(APIView):
    authentication_classes = []
    # TODO put an actual permission
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Odoo will post a JSON payload with the employee data
        on creation or update
        """
        sync_employee.delay(request.data)
        return Response({"status":"queued"}, status=status.HTTP_200_OK)

class SyncContractHook(APIView):
    authentication_classes = []
    # TODO put an actual permission
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Odoo will post a JSON payload with the employee data
        on creation or update
        """
        sync_contract.delay(request.data)
        return Response({"status":"queued"}, status=status.HTTP_200_OK)
    
class FieldWorkerListView(generics.ListAPIView):
    """
    View for listing all field workers with filtering, searching and pagination
    """
    queryset = FieldWorker.objects.all()
    serializer_class = FieldWorkerListSerializer
    filterset_class = FieldWorkerFilter
    ordering_fields = [
        'name',
        'start_date',
        'created_at',
    ]
    ordering = ['-created_at']
    search_fields = ['name', 'identification_number']

    @method_decorator(cache_page(60 * 15)) # 15 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        # Look if inactive records specifically requested
        include_inactive = self.request.query_params.get('include_inactive', 'false').lower()
        if include_inactive == 'true':
            return self.queryset.all()
        return self.queryset.filter(is_active=True)

class FieldWorkerDetailView(generics.RetrieveAPIView):
    queryset = FieldWorker.objects.all()
    serializer_class = FieldWorkerDetailSerializer

    @method_decorator(cache_page(60 * 15))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
class FarmViewSet(viewsets.ModelViewSet):
    queryset = Farm.objects.all()
    serializer_class = FarmSerializer

class ActivityGroupSet(viewsets.ModelViewSet):
    queryset = ActivityGroup.objects.all()
    serializer_class = ActivityGroupSerializer
    search_fields = ['name']

class ActivitySet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    filterset_fields = ['activity_group', 'labor_type', 'uom']
    search_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            qs = qs.select_related("activity_group", "labor_type", "uom")
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ActivityDetailSerializer
        return super().get_serializer_class()
    
class UomViewSet(viewsets.ModelViewSet):
    queryset = Uom.objects.all()
    serializer_class = UomSerializer
    search_fields = ['name']

class LaborTypeViewSet(viewsets.ModelViewSet):
    queryset = LaborType.objects.all()
    serializer_class = ActivitySerializer
    filterset_fields = ['calculates_integral', 'calculates_thirteenth_bonus', 'calculates_fourteenth_bonus']
    search_fields = ['name']

class TariffViewSet(viewsets.ModelViewSet):
    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer
    filterset_fields = ['activity', 'farm']
    search_fields = ['name']

class PayrollBatchViewSet(viewsets.ModelViewSet):
    queryset = PayrollBatch.objects.all()
    serializer_class = PayrollBatchSerializer
    filterset_fields = ['status']
    search_fields = ['name']

class PayrollConfigurationView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/configuration/ → returns the singleton config
    PATCH/PUT  /api/v1/configuration/ → update fields on that single row
    """
    serializer_class = PayrollConfigurationSerializer
    
    def get_object(self):
        obj, _ = PayrollConfiguration.objects.get_or_create(
            pk=1,
            defaults={
                "mobilization_percentage": 0.0,
                "extra_hours_percentage": 0.0,
                "basic_monthly_wage": 0.0,
            }
        )
        return obj