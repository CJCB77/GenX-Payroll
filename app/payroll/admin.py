from django.contrib import admin

from .models import FieldWorker

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

admin.site.register(FieldWorker, FieldWorkerAdmin)
