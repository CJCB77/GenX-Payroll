from django.db.models import Sum
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

def calculate_thirteenth_bonus(daily_wage, extra_hours, only_extra_hours=False):
    daily_thirteenth_bonus = daily_wage / MONTHS_IN_YEAR
    total_thirteenth_bonus = extra_hours + (daily_thirteenth_bonus if not only_extra_hours else 0) 
    return total_thirteenth_bonus

def calculate_fourteenth_bonus(worker):
    config = PayrollConfiguration.get_config()
    basic_wage = config.basic_monthly_wage

    daily_fourteenth_bonus = (basic_wage / MONTHS_IN_YEAR) / DAYS_OF_THE_MONTH
    return daily_fourteenth_bonus


def compute_inline_calculations(line: PayrollBatchLine):
    worker = line.field_worker
    daily_wage = (worker.wage or 0) / Decimal(DAYS_OF_THE_MONTH)
    try:
        tariff = Tariff.objects.get(activity= line.activity, farm = line.payroll_batch.farm)
        tariff_price = tariff.cost_per_unit
    except Tariff.DoesNotExist:
        tariff_price = 0
    
    line_is_weekend = line.date.weekday() >= 5

    total_cost = line.quantity * tariff_price
    if line_is_weekend:
        surplus = total_cost
    else:
        surplus = max(Decimal(0), total_cost - daily_wage)

    mobilization = calculate_mobilization(surplus)
    extra_hours, extra_hours_qty = calculate_extra_hours(surplus, worker)
    thirteenth_bonus = calculate_thirteenth_bonus(daily_wage, extra_hours, only_extra_hours=line_is_weekend)
    fourthteenth_bonus = calculate_fourteenth_bonus(worker)

    return {
        "total_cost": total_cost,
        "salary_surplus": surplus,
        "mobilization_bonus": mobilization,
        "extra_hours_value": extra_hours,
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
    # Clear all integral bonuses for this worker in this week
    PayrollBatchLine.objects.filter(
        field_worker=worker,
        payroll_batch=payroll_batch,
    ).update(integral_bonus=0)

    # Get all the lines of this worker in this week for the payroll batch
    fw_work_lines = PayrollBatchLine.objects.filter(
        field_worker=worker, 
        payroll_batch=payroll_batch,
        activity__labor_type__calculates_integral=True 
    )

    # Get distinc count of worked days
    worked_days = fw_work_lines.values_list('date', flat=True).distinct().count()
    integral_bonus = calculate_integral_bonus(worker.wage, worked_days)
    if integral_bonus == 0:
        return
    
    distributed_integral_bonus = integral_bonus / worked_days
    for line in fw_work_lines:
            line.integral_bonus = Decimal(distributed_integral_bonus)
            line.save()
            
def recalc_same_day_for_worker(worker, payroll_batch, date):
    """
    If a worker has more than one line for the same day, distribute calculations proportionally
    """
    line_is_weekend = date.weekday() >= 5
    fw_daily_wage = worker.wage / DAYS_OF_THE_MONTH
    # Get all lines for this worker's day
    fw_lines = PayrollBatchLine.objects.filter(
        payroll_batch=payroll_batch,
        date=date,
        field_worker=worker
    )
    if not fw_lines.exists():
        return
    
    lines_total_cost = fw_lines.aggregate(total_cost=Sum('total_cost'))['total_cost']
    total_salary_surplus = (lines_total_cost - fw_daily_wage) if not line_is_weekend else lines_total_cost
    for line in fw_lines:
        proportion = line.total_cost / lines_total_cost
        line.salary_surplus = total_salary_surplus * proportion
        line.mobilization_bonus = calculate_mobilization(line.salary_surplus)
        line.extra_hours_value, line.extra_hours_qty = calculate_extra_hours(line.salary_surplus, worker)
        line.thirteenth_bonus = calculate_thirteenth_bonus(
            daily_wage=fw_daily_wage * proportion, 
            extra_hours=line.extra_hours_value, 
            only_extra_hours=line_is_weekend
        )
        line.fourteenth_bonus = calculate_fourteenth_bonus(worker) * proportion
        line.integral_bonus = line.integral_bonus * proportion
        line.save()

    

