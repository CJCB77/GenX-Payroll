from rest_framework import serializers
from .models import (
    FieldWorker,
    Activity,
    LaborType,
    Uom,
    ActivityGroup,
    Farm,
    Tariff,
    PayrollBatch,
    PayrollBatchLine, 
    PayrollConfiguration,
)

import logging

logger = logging.getLogger(__name__)

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

class ActivityGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityGroup
        fields = ['id','name', 'code', 'description']
        read_only_fields = ['id', 'created_at', 'updated_at']

class UomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Uom
        fields = ['id','name']
        read_only_fields = ['id', 'created_at', 'updated_at']

class LaborTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaborType
        fields = ['id','name', 'code', 'calculates_integral', 'calculates_thirteenth_bonus', 'calculates_fourteenth_bonus']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ['id','name', 'activity_group', 'labor_type', 'uom']

class ActivityDetailSerializer(serializers.ModelSerializer):
    activity_group = ActivityGroupSerializer(read_only=True)
    labor_type = LaborTypeSerializer(read_only=True)
    uom = UomSerializer(read_only=True)
    class Meta:
        model = Activity
        fields = ['id','name', 'activity_group', 'labor_type', 'uom']
        read_only_fields = ['id', 'created_at', 'updated_at']

class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ['id','name', 'activity', 'farm', 'cost_per_unit']
        read_only_fields = ['id', 'created_at', 'updated_at']

class PayrollBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollBatch
        fields = ['id','name', 'start_date', 'end_date', 'status', 'farm']
        read_only_fields = ['id', 'created_at', 'updated_at']

class PayrollConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollConfiguration
        fields = [
            "mobilization_percentage",
            "extra_hours_percentage",
            "basic_monthly_wage",
            "extra_hour_multiplier",
            "daily_payroll_line_worker_limit",
        ]

class PayrollBatchLineWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollBatchLine
        fields = [
            'id',
            'date',
            'iso_week',
            'iso_year',
            'field_worker', 
            'activity', 
            'quantity',
            'total_cost',
            'salary_surplus',
            'integral_bonus',
            'mobilization_bonus',
            'extra_hours_value',
            'extra_hours_qty',
            'thirteenth_bonus',
            'fourteenth_bonus', 
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'iso_year',
            'iso_week',
            'total_cost',
            'salary_surplus',
            'integral_bonus',
            'mobilization_bonus',
            'extra_hours_value',
            'extra_hours_qty',
            'thirteenth_bonus',
            'fourteenth_bonus',
        ]
    
    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Check how many configs are available
        config = PayrollConfiguration.objects.all().first()
        # Check daily limit 
        daily_limit = PayrollConfiguration.objects.get_config().daily_payroll_line_worker_limit
        if daily_limit and daily_limit > 0:
            qs = PayrollBatchLine.objects.filter(
                field_worker=attrs['field_worker'],
                date=attrs['date']
            )

            # If updating an existing line, exclude itself
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.count() >= daily_limit:
                raise serializers.ValidationError({
                    'daily_limit': f"Daily limit of {daily_limit} lines per worker has been reached."
                })
        return attrs

class PayrollBatchLineSerializer(serializers.ModelSerializer):
    payroll_batch = PayrollBatchSerializer(read_only=True)
    field_worker = FieldWorkerListSerializer(read_only=True)
    activity = ActivityDetailSerializer(read_only=True)

    class Meta:
        model = PayrollBatchLine
        fields = [
            'id', 
            'payroll_batch', 
            'field_worker', 
            'date',
            'iso_week', 
            'activity', 
            'quantity', 
            'total_cost', 
            'salary_surplus', 
            'integral_bonus', 
            'mobilization_bonus', 
            'extra_hours_value', 
            'extra_hours_qty', 
            'thirteenth_bonus', 
            'fourteenth_bonus',
        ]
        read_only_fields = [
            'id', 
            'created_at', 
            'updated_at',
            'total_cost',
            'salary_surplus',
            'integral_bonus',
            'mobilization_bonus',
            'extra_hours_value',
            'extra_hours_qty',
            'thirteenth_bonus',
            'fourteenth_bonus',
        ]