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

class FieldWorkerDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for field worker details
    """
    class Meta:
        model = FieldWorker
        fields = '__all__'

class FieldWorkerListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing field workers
    """
    class Meta:
        model = FieldWorker
        fields = [
            'id',
            'odoo_employee_id',
            'name',
            'identification_number',
            'contract_status',
            'wage',
            'email',
        ]
        read_only_fields = ['__all__']

class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = ['id','name', 'code', 'description']
        read_only_fields = ['id', 'created_at', 'updated_at']