from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, generics
from rest_framework.permissions import AllowAny
from payroll.tasks import (
    sync_employee, 
    sync_contract,
    recalc_line_task,
    recalc_delete_task,
    import_payroll_file
)
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
    PayrollConfiguration,
    PayrollBatchLine
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
    TariffSerializer,
    PayrollBatchLineSerializer,
    PayrollBatchLineWriteSerializer,
    LaborTypeSerializer,
    PayrollBatchImportSerializer
)
from .filters import (
    FieldWorkerFilter,
    PayrollLineFilter
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
    serializer_class = LaborTypeSerializer
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

    def get_serializer_class(self):
        if self.action == "import_lines":
            return PayrollBatchImportSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        batch = self.get_object()
        return Response({"status": batch.status, "error_message": batch.error_message})
    
    @action(detail=True, methods=['post'], url_path='import-lines')
    def import_lines(self, request, pk=None):
        batch = self.get_object()
        serializer = PayrollBatchImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        batch.status = 'processing'
        batch.save(update_fields=['status'])

        # Save uploaded file to a temp location
        upload = serializer.validated_data['file']
        temp_path = default_storage.save(
            f"temp/payroll_batch_{batch.id}_{upload.name}",
            ContentFile(upload.read())
        )

        # Fire and forget the import task
        import_payroll_file(batch.id, temp_path)

        return Response(
            {"detail": "Payroll batch import queued"},
            status=status.HTTP_202_ACCEPTED
        )



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
                "extra_hour_multiplier": 0.0
            }
        )
        return obj

class PayrollBatchLineViewSet(viewsets.ModelViewSet):
    """
    - GET /api/payroll-lines/ → returns all lines
    - GET /api/payroll-batches/<batch_pk>/payroll-lines/ → returns lines for a specific batch
    - POST /api/payroll-batches/<batch_pk>/payroll-lines/ → creates a new line
    - PATCH /api/payroll-batches/<batch_pk>/payroll-lines/<pk>/ → updates a line & recalculates
    - DELETE /api/payroll-batches/<batch_pk>/payroll-lines/<pk>/ → deletes a line
    - POST /api/payroll-batches/<batch_pk>/payroll-lines/batch-import/ → uploads a CSV/XLSX
    """
    queryset = PayrollBatchLine.objects.select_related("payroll_batch", "field_worker", "activity")
    filterset_class = PayrollLineFilter
    serializer_class = PayrollBatchLineSerializer

    def get_queryset(self):
        # If nested under a batch, filter by that batch
        batch_pk = self.kwargs.get("batch_pk")
        if batch_pk:
            return self.queryset.filter(payroll_batch=batch_pk)
        return self.queryset

    def get_serializer_class(self):
        if self.action in ('create','update','partial_update'):
            return PayrollBatchLineWriteSerializer
        return PayrollBatchLineSerializer

    def perform_create(self, serializer):
        # Set the batch from the param
        batch_pk = self.kwargs.get("batch_pk")
        batch = get_object_or_404(PayrollBatch, pk=batch_pk)

        batch.status = 'processing'
        batch.save(update_fields=['status'])

        # Create the line
        line = serializer.save(payroll_batch=batch)
        
        recalc_line_task.delay(line.id, recalc_week=True)
    
    def perform_update(self, serializer):
        # Original activity may have changed
        original_activity = serializer.instance.activity
        line = serializer.save()
        activity_changed = original_activity != line.activity

        batch = line.payroll_batch
        batch.status = 'processing'
        batch.save(update_fields=['status'])

        # Recalculate the line
        recalc_line_task.delay(line.id, recalc_week=activity_changed)
    
    def perform_destroy(self, instance):
        # Get the week the line that was deleted
        worker_id = instance.field_worker.id
        payroll_batch_id = instance.payroll_batch.id
        date = instance.date.isoformat()

        super().perform_destroy(instance)
        
        batch = PayrollBatch.objects.get(pk=payroll_batch_id)
        batch.status = 'processing'
        batch.save(update_fields=['status'])

        recalc_delete_task.delay(worker_id, payroll_batch_id, date)
    