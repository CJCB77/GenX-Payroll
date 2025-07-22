from django_filters import rest_framework as filters
from .models import FieldWorker


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
            'odoo_employee_id', 
            'odoo_contract_id', 
            'wage',
            'email',
            'contract_status',
            'is_active',
        ]