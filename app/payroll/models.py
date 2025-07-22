from django.db import models
from django.utils import timezone
from django.conf import settings


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

class Farm(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=8, unique=True)
    description = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['code']),
        ]

class ActivityGroup(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=8, unique=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        indexes = [
            models.Index(fields=['code']),
        ]

class LaborType(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=8, unique=True)
    calculates_integral = models.BooleanField(default=True)
    calculates_thirteenth_bonus = models.BooleanField(default=True)
    calculates_fourteenth_bonus = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Uom(models.Model):
    """Unit of measurement"""
    name = models.CharField(max_length=255, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Activity(models.Model):

    name = models.CharField(max_length=255, unique=True)
    activity_group = models.ForeignKey(ActivityGroup, on_delete=models.CASCADE)
    labor_type = models.ForeignKey(LaborType, on_delete=models.CASCADE)
    uom = models.ForeignKey(Uom, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['activity']),
            models.Index(fields=['labor_type']),
        ]

class Tariff(models.Model):
    """Activity tariffs by farm"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['activity', 'farm'],
                name='unique_activity_farm',
            )
        ]


class PayrollBatch(models.Model):
    """Represent a batch of payroll data uploaded weekly by a user"""    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    name = models.CharField(max_length=255, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

class PayrollBatchLine(models.Model):
    # Input fields
    payroll_batch = models.ForeignKey(PayrollBatch, on_delete=models.CASCADE)
    date = models.DateField()
    field_worker = models.ForeignKey(FieldWorker, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    # Output calculation fields
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    salary_surplus = models.DecimalField(max_digits=10, decimal_places=2)
    integral_bonus = models.DecimalField(max_digits=10, decimal_places=2)
    mobilization_bonus = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hours_value = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hours_qty = models.DecimalField(max_digits=10, decimal_places=2)
    thirteenth_bonus = models.DecimalField(max_digits=10, decimal_places=2)
    fourteenth_bonus = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['payroll_batch']),
            models.Index(fields=['field_worker']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields = ['payroll_batch', 'field_worker', 'activity'],
                name = 'unique_payroll_batch_line',
            )
        ]