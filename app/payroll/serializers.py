from rest_framework import serializers
from .models import (
    FieldWorker,
    Activity,
    LaborType,
    Uom,
    ActivityGroup,
    Farm,
    Tariff,
    PayrollBatch
)

class FieldWorkerSerializer(serializers.ModelSerializer):
    """
    Serializer for field worker details
    """
    class Meta:
        model = FieldWorker
        fields = '__all__'
        read_only_fields = fields

class FieldWorkerListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing field workers
    """
    class Meta:
        model = FieldWorker
        fields = [
            'odoo_employee_id',
            'name',
            'identification_number',
            'contract_status',
            'wage',
            'email',
        ]
        read_only_fields = '__all__'