from django.contrib import admin

from .models import (
    FieldWorker,
    PayrollConfiguration
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

admin.site.register(FieldWorker, FieldWorkerAdmin)
admin.site.register(PayrollConfiguration, PayrollConfigurationAdmin)