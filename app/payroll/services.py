from decimal import Decimal
from .models import (
    PayrollBatchLine,
    FieldWorker, 
    Tariff,
    PayrollConfiguration
)
import logging

WORK_HOURS_PER_DAY = 8
DAYS_OF_THE_MONTH = 30

logger = logging.getLogger(__name__)

def calculate_mobilization(surplus):
    config = PayrollConfiguration.get_config()
    mobilization = surplus * (config.mobilization_percentage / 100)

    return mobilization

def calculate_extra_hours(surplus,worker):
    config = PayrollConfiguration.get_config()
    wage = worker.wage

    extra_hours_value = surplus * (config.extra_hours_percentage / 100)

    if extra_hours_value > 0:
        hourly_wage = (wage / DAYS_OF_THE_MONTH) / WORK_HOURS_PER_DAY
        extra_hour_wage = hourly_wage * config.extra_hour_multiplier
        extra_hours_qty = extra_hours_value / extra_hour_wage
        
    return extra_hours_value, extra_hours_qty


def compute_line_totals(line: PayrollBatchLine):
    worker = line.field_worker
    daily_wage = worker.wage / Decimal(30)
    logger.info(f"Daily wage: {daily_wage}")
    try:
        tariff = Tariff.objects.get(activity= line.activity, farm = line.payroll_batch.farm)
        tariff_price = tariff.cost_per_unit
    except Tariff.DoesNotExist:
        tariff_price = 0
    logger.info(f"Tariff price: {tariff_price}")
    total_cost = line.quantity * tariff_price
    surplus = max(Decimal(0), total_cost - daily_wage)

    mobilization = calculate_mobilization(surplus)
    extra_hours, extra_hours_qty = calculate_extra_hours(surplus, worker)

    return {
        "total_cost": total_cost,
        "surplus": surplus,
        "mobilization": mobilization,
        "extra_hours": extra_hours,
        "extra_hours_qty": extra_hours_qty
    }
    