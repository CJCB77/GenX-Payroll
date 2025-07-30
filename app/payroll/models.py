from decimal import Decimal
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
    name = models.CharField(max_length=255, unique=True)
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
            models.Index(fields=['activity_group']),
            models.Index(fields=['labor_type']),
        ]

class Tariff(models.Model):
    """Activity tariffs by farm"""
    name = models.CharField(max_length=255, unique=True)
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
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    iso_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    iso_week = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    def save(self, *args, **kwags):
        year, week, _weekday = self.start_date.isocalendar()
        self.iso_week = week
        self.iso_year = year
        super().save(*args, **kwags)

class PayrollBatchLine(models.Model):
    # Input fields
    payroll_batch = models.ForeignKey(PayrollBatch, on_delete=models.CASCADE)
    date = models.DateField()
    field_worker = models.ForeignKey(FieldWorker, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    iso_week = models.PositiveSmallIntegerField(editable=False)
    iso_year = models.PositiveSmallIntegerField(editable=False)

    # Output calculation fields
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_surplus = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    integral_bonus = models.DecimalField(max_digits=10, decimal_places=2,
                                         null=True, blank=True, default=Decimal(0.00))
    mobilization_bonus = models.DecimalField(max_digits=10, decimal_places=2, 
                                             null=True, blank=True, default=Decimal(0.00))
    extra_hours_value = models.DecimalField(max_digits=10, decimal_places=2, 
                                            null=True, blank=True, default=Decimal(0.00))
    extra_hours_qty = models.DecimalField(max_digits=10, decimal_places=2, 
                                          null=True, blank=True, default=Decimal(0.00))
    thirteenth_bonus = models.DecimalField(max_digits=10, decimal_places=2, 
                                           null=True, blank=True, default=Decimal(0.00))
    fourteenth_bonus = models.DecimalField(max_digits=10, decimal_places=2, 
                                           null=True, blank=True, default=Decimal(0.00))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwags):
        year, week, _ = self.date.isocalendar()
        self.iso_week = week
        self.iso_year = year
        super().save(*args, **kwags)
  

    class Meta:
        indexes = [
            models.Index(fields=['payroll_batch']),
            models.Index(fields=['field_worker']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields = ['field_worker', 'activity', 'date'],
                name = 'unique_payroll_batch_line',
            )
        ]

class PayrollConfigurationManager(models.Manager):
    def get_config(self):
        """
        Get the singleton config instance
        """
        config, _ = self.get_or_create(
            pk=1,
            defaults={
                "mobilization_percentage": Decimal(0.0),
                "extra_hours_percentage": Decimal(0.0),
                "basic_monthly_wage": Decimal(0.0),
                "extra_hour_multiplier": Decimal(0.0),
                "daily_payroll_line_worker_limit": 3
            }
        )
        return config

class PayrollConfiguration(models.Model):
    """Payroll configuration"""
    # Prevent multiple instances
    id = models.AutoField(primary_key=True)

    mobilization_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hours_percentage = models.DecimalField(max_digits=10, decimal_places=2)
    extra_hour_multiplier = models.DecimalField(max_digits=10, decimal_places=2)
    basic_monthly_wage = models.DecimalField(max_digits=10, decimal_places=2)
    daily_payroll_line_worker_limit = models.PositiveSmallIntegerField(default=3)

    objects = PayrollConfigurationManager()

    def save(self, *args, **kwags):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwags)

    def delete(self, *args, **kwags):
        # Prevent deletion
        pass

    @classmethod
    def get_config(cls):
        return cls.objects.get_config()

    def __str__(self):
        return "Payroll Configuration"