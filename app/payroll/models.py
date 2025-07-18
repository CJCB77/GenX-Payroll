from django.db import models
from django.utils import timezone


class FieldWorker(models.Model):
    odoo_employee_id = models.IntegerField(unique=True, db_index=True)
    odoo_contract_id = models.IntegerField(unique=True, null=True, blank=True)

    # From Odooo employee table
    name = models.CharField(max_length=255)
    mobile_phone = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    identification_number = models.CharField(max_length=10, unique=True)

    # From Odoo contract table
    wage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    contract_status = models.CharField(max_length=255, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        indexes = [
            models.Index(fields=['odoo_employee_id']),
            models.Index(fields=['odoo_contract_id']),
            models.Index(fields=['is_active']),
        ]