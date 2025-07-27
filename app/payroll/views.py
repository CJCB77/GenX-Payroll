from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, generics
from rest_framework.permissions import AllowAny
from .tasks import sync_employee, sync_contract
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import os
from .models import (
    FieldWorker,
    Farm,    
    ActivityGroup,
    Activity,
    LaborType,
    Uom,
    Tariff
)
from .serializers import (
    FieldWorkerListSerializer,
    FieldWorkerDetailSerializer,
    FarmSerializer,
    ActivityGroupSerializer,
    ActivitySerializer,
    UomSerializer,
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
        logger.info(f"Received an employee payload: {request.data}")
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
        logger.info(f"Received a contract payload: {request.data}")
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

class UomViewSet(viewsets.ModelViewSet):
    queryset = Uom.objects.all()
    serializer_class = UomSerializer
    search_fields = ['name']

class LaborTypeViewSet(viewsets.ModelViewSet):
    queryset = LaborType.objects.all()
    serializer_class = ActivitySerializer
    filterset_fields = ['calculates_integral', 'calculates_thirteenth_bonus', 'calculates_fourteenth_bonus']
    search_fields = ['name']