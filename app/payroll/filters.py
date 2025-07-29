from django_filters import rest_framework as filters
from .models import FieldWorker, PayrollBatchLine


class FieldWorkerFilter(filters.FilterSet):
    """
    Custom filter class for advanced filtering options
    """
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')

    # Range filters for wage
    wage_min = filters.NumberFilter(field_name='wage', lookup_expr='gte')
    wage_max = filters.NumberFilter(field_name='wage', lookup_expr='lte')

    # Date range filters
    start_date_after = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_after = filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_before = filters.DateFilter(field_name='end_date', lookup_expr='lte')

    class Meta:
        model = FieldWorker
        fields = [
            'id',
            'odoo_employee_id', 
            'odoo_contract_id', 
            'identification_number',
            'wage',
            'email',
            'contract_status',
            'is_active',
        ]

class PayrollLineFilter(filters.FilterSet):
    """
    Custom payroll line filter class for advanced filtering options
    """
    # Date range
    date__gte = filters.DateFilter(field_name="date", lookup_expr="gte")
    date__lte = filters.DateFilter(field_name="date", lookup_expr="lte")
    # Worker, activity, batch
    field_worker__id = filters.CharFilter(field_name="field_worker__identification_number", lookup_expr="icontains")
    field_worker__name = filters.CharFilter(field_name="field_worker__name", lookup_expr="icontains")
    activity__name = filters.CharFilter(field_name="activity__name", lookup_expr="icontains")
    payroll_batch__name = filters.CharFilter(field_name="payroll_batch__name", lookup_expr="icontains")

    #Numerics ranges for computed fields
    total_cost__gte = filters.NumberFilter(field_name="total_cost", lookup_expr="gte")
    total_cost__lte = filters.NumberFilter(field_name="total_cost", lookup_expr="lte")
    integral_bonus__gte = filters.NumberFilter(field_name="integral_bonus", lookup_expr="gte")
    integral_bonus__lte = filters.NumberFilter(field_name="integral_bonus", lookup_expr="lte")

    class Meta:
        model = PayrollBatchLine
        fields = [
            'date',
            'iso_week',
            'activity',
            'payroll_batch',
        ]