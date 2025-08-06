from django.contrib import admin

from .models import (
    FieldWorker,
    PayrollConfiguration,
    PayrollBatchLine,
    PayrollBatch,
    Activity,
    ActivityGroup,
    Farm,
    LaborType,
    Uom,
    Tariff
)

class FieldWorkerAdmin(admin.ModelAdmin):
    ordering = ['odoo_employee_id']
    list_display = ('name','identification_number', 'odoo_employee_id', 'odoo_contract_id', 'is_active')
    fieldsets = (
        ("Odoo information", {"fields": ["odoo_employee_id", "odoo_contract_id"]}),
        ("Employee information", {"fields": [
            "name", "mobile_phone", "email", "identification_number", 
            "wage", "start_date", "end_date", "contract_status", "is_active"]}),
        ("Date information", {"fields": ["last_sync", "created_at", "updated_at"]}),
    )
    readonly_fields = ['last_sync', 'created_at', 'updated_at', 'odoo_employee_id', 'odoo_contract_id']
    search_fields = ['name', 'identification_number','odoo_employee_id']

class PayrollConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        '__str__', 
        'extra_hours_percentage', 
        'mobilization_percentage', 
        'basic_monthly_wage', 
    )
    fieldsets = (
        ("Line configurations", {"fields": [
            "extra_hours_percentage",
            "mobilization_percentage",
            "extra_hour_value",
        ]}),
        ("System wide configurations", {"fields": [
            "basic_monthly_wage",
            "daily_payroll_line_worker_limit",
        ]}),
    )

class PayrollBatchLineAdmin(admin.ModelAdmin):
    list_display = (
        'field_worker', 
        'date',
        'activity',
        'quantity',
        'total_cost',
        'salary_surplus',
        'extra_hours_value', 
        'mobilization_bonus',
        'thirteenth_bonus', 
        'fourteenth_bonus',
        'integral_bonus'
    )
    list_filter = ('date', 'field_worker')
    search_fields = ['field_worker__name', 'field_worker__identification_number']

class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'description')

class ActivityGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')

class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'activity_group', 'labor_type', 'uom')

class LaborTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'calculates_integral', 'calculates_thirteenth_bonus', 'calculates_fourteenth_bonus')
    
class UomAdmin(admin.ModelAdmin):
    list_display = ('name',)


class TariffAdmin(admin.ModelAdmin):
    list_display = ('name', 'activity', 'farm', 'cost_per_unit')

admin.site.register(PayrollBatchLine, PayrollBatchLineAdmin)
admin.site.register(PayrollBatch)

admin.site.register(Farm, FarmAdmin)
admin.site.register(ActivityGroup, ActivityGroupAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(LaborType, LaborTypeAdmin)
admin.site.register(Uom, UomAdmin)
admin.site.register(Tariff, TariffAdmin)

admin.site.register(FieldWorker, FieldWorkerAdmin)
admin.site.register(PayrollConfiguration, PayrollConfigurationAdmin)