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
MONTHS_IN_YEAR = 12

logger = logging.getLogger(__name__)

def calculate_mobilization(surplus):
    config = PayrollConfiguration.get_config()
    mobilization = surplus * (config.mobilization_percentage / 100)

    return mobilization

def calculate_extra_hours(surplus,worker):
    config = PayrollConfiguration.get_config()
    wage = worker.wage

    extra_hours_value = surplus * (config.extra_hours_percentage / 100)
    extra_hours_qty = 0

    if extra_hours_value > 0:
        hourly_wage = (wage / DAYS_OF_THE_MONTH) / WORK_HOURS_PER_DAY
        extra_hour_wage = hourly_wage * config.extra_hour_multiplier
        extra_hours_qty = extra_hours_value / extra_hour_wage
        
    return extra_hours_value, extra_hours_qty

def calculate_thirteenth_bonus(worker):
    fw_wage = worker.wage 

    daily_thirteenth_bonus = (fw_wage / MONTHS_IN_YEAR) / DAYS_OF_THE_MONTH
    return daily_thirteenth_bonus

def calculate_fourteenth_bonus(worker):
    config = PayrollConfiguration.get_config()
    basic_wage = config.basic_monthly_wage

    daily_fourteenth_bonus = (basic_wage / MONTHS_IN_YEAR) / DAYS_OF_THE_MONTH
    return daily_fourteenth_bonus


def compute_inline_calculations(line: PayrollBatchLine):
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
    thirteenth_bonus = calculate_thirteenth_bonus(worker)
    fourthteenth_bonus = calculate_fourteenth_bonus(worker)

    return {
        "total_cost": total_cost,
        "surplus": surplus,
        "mobilization": mobilization,
        "extra_hours": extra_hours,
        "extra_hours_qty": extra_hours_qty,
        "thirteenth_bonus": thirteenth_bonus,
        "fourteenth_bonus": fourthteenth_bonus,
    }

def calculate_integral_bonus(worker_wage, worked_days):
    worker_daily_wage = worker_wage / DAYS_OF_THE_MONTH
    if worked_days >= 5:
        integral_bonus = worker_daily_wage * 2
    elif worked_days == 4:
        integral_bonus = worker_daily_wage
    else:
        integral_bonus = 0
    return integral_bonus

def compute_weekly_integral_for_worker(worker, payroll_batch):
    # Get all the lines of this worker in this week for the payroll batch
    fw_lines = PayrollBatchLine.objects.filter(
        field_worker=worker, 
        payroll_batch=payroll_batch, 
    )
    # Get distinc count of worked days
    worked_days = fw_lines.values_list('date', flat=True).distinct().count()
    integral_bonus = calculate_integral_bonus(worker.wage, worked_days)
    if integral_bonus == 0:
        return
    
    distributed_integral_bonus = integral_bonus / worked_days
    for line in fw_lines:
            line.integral_bonus = Decimal(distributed_integral_bonus)
            line.save()
            

    

