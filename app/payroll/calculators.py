from abc import ABC, abstractmethod
from django.db import transaction
from typing import Dict, Any, List
from django.db.models import Sum
from decimal import Decimal
from .models import (
    PayrollBatchLine,
    Tariff,
    PayrollConfiguration
)
from .constants import DAYS_OF_THE_MONTH, WORK_HOURS_PER_DAY, MONTHS_IN_YEAR
import logging

logger = logging.getLogger(__name__)

class PayrollCalculatorInterface(ABC):
    """Interface for payroll calculations"""

    @abstractmethod
    def calculate(self, context: Dict[str, Any]) -> None:
        pass

class BasePayrollCalculator(PayrollCalculatorInterface):
    """
    Base calculator with shared calculations
    """
    def _get_daily_wage(self, worker):
        return (worker.wage or Decimal(0)) / Decimal(DAYS_OF_THE_MONTH)
    
    def _get_tariff_price(self, line):
        try:
            tariff = Tariff.objects.get(activity= line.activity, farm = line.payroll_batch.farm)
            return tariff.cost_per_unit
        except Tariff.DoesNotExist:
            return Decimal(0)
    
    def _is_weekend(self, line):
        return line.date.weekday() >= 5
    
    def _get_surplus(self, total_cost, daily_wage, is_weekend):
        if is_weekend:
            return total_cost
        else:
            return max(Decimal(0), total_cost - daily_wage)
    
    def _calculate_mobilization(self, surplus):
        config = PayrollConfiguration.get_config()
        mobilization = surplus * (config.mobilization_percentage / 100)
        return mobilization

    def _calculate_extra_hours(self, surplus):
        config = PayrollConfiguration.get_config()
        extra_hours_value = surplus * (config.extra_hours_percentage / 100)

        return extra_hours_value

    def _calculate_extra_hours_qty(self, extra_hours_value, worker):
        if extra_hours_value <= 0:
            return Decimal(0)
        
        config = PayrollConfiguration.get_config()
        hourly_wage = (worker.wage / DAYS_OF_THE_MONTH) / WORK_HOURS_PER_DAY
        extra_hour_wage = hourly_wage * config.extra_hour_multiplier
        extra_hours_qty = extra_hours_value / extra_hour_wage

        return extra_hours_qty

    def _calculate_thirteenth_bonus(self, daily_wage, extra_hours_value, is_weekend=False):
        daily_thirteenth_bonus = daily_wage / MONTHS_IN_YEAR

        return extra_hours_value + (daily_thirteenth_bonus if not is_weekend else Decimal(0))
        
    def _calculate_fourteenth_bonus(self, worker):
        config = PayrollConfiguration.get_config()
        basic_wage = config.basic_monthly_wage

        daily_fourteenth_bonus = (basic_wage / MONTHS_IN_YEAR) / DAYS_OF_THE_MONTH
        return daily_fourteenth_bonus

class InlineCalculator(BasePayrollCalculator):
    """Single Responsability: Calculate fields based on single line data"""

    def calculate(self, context: Dict[str, Any]) -> None:
        line = context['line']
        worker = line.field_worker

        daily_wage = self._get_daily_wage(worker)
        tariff_price = self._get_tariff_price(line)
        is_weekend = self._is_weekend(line)

        line.total_cost = line.quantity * tariff_price
        line.salary_surplus = self._get_surplus(line.total_cost, daily_wage, is_weekend)
        line.mobilization_bonus = self._calculate_mobilization(line.salary_surplus)
        line.extra_hours_value = self._calculate_extra_hours(line.salary_surplus)
        line.extra_hours_qty = self._calculate_extra_hours_qty(line.extra_hours_value, worker)
        line.thirteenth_bonus = self._calculate_thirteenth_bonus(daily_wage, line.extra_hours_value, is_weekend)
        line.fourteenth_bonus = self._calculate_fourteenth_bonus(worker)

        line.save()
    
    def calculate_batch(self, lines):
        updated_lines = []

        for line in lines:
            worker = line.field_worker
            daily_wage = self._get_daily_wage(worker)
            tariff_price = self._get_tariff_price(line)
            is_weekend = self._is_weekend(line)

            line.total_cost = line.quantity * tariff_price
            line.salary_surplus = self._get_surplus(line.total_cost, daily_wage, is_weekend)
            line.mobilization_bonus = self._calculate_mobilization(line.salary_surplus)
            line.extra_hours_value = self._calculate_extra_hours(line.salary_surplus)
            line.extra_hours_qty = self._calculate_extra_hours_qty(line.extra_hours_value, worker)
            line.thirteenth_bonus = self._calculate_thirteenth_bonus(daily_wage, line.extra_hours_value, is_weekend)
            line.fourteenth_bonus = self._calculate_fourteenth_bonus(worker)

            updated_lines.append(line)

        PayrollBatchLine.objects.bulk_update(
            updated_lines, 
            ['total_cost', 'salary_surplus', 'mobilization_bonus', 'extra_hours_value', 
             'extra_hours_qty', 'thirteenth_bonus', 'fourteenth_bonus']
        )

        return updated_lines
        
class DayLevelCalculator(BasePayrollCalculator):
    """Single Responsability: Calculate proportional bonuse for same-day lines"""

    def calculate(self, context: Dict[str, Any]) -> None:
        worker = context['worker']
        payroll_batch = context['payroll_batch']
        date = context['date']

        self._recalculate_same_day_proportions(worker, payroll_batch, date)
    
    def _recalculate_same_day_proportions(self, worker, payroll, date) -> None:
        is_weekend = date.weekday() >= 5
        daily_wage = worker.wage / DAYS_OF_THE_MONTH

        fw_lines = PayrollBatchLine.objects.filter(
            payroll_batch=payroll,
            date=date,
            field_worker=worker
        )
        if not fw_lines.exists():
            return
        
        lines_total_cost = fw_lines.aggregate(total_cost=Sum('total_cost'))['total_cost']
        total_salary_surplus = (lines_total_cost - daily_wage) if not is_weekend else lines_total_cost
        for line in fw_lines:
            proportion = line.total_cost / lines_total_cost
            self._update_line_with_proportion(line, proportion, total_salary_surplus, daily_wage, is_weekend)
    
    def _update_line_with_proportion(self, line, proportion, total_salary_surplus, daily_wage, is_weekend):
        line.salary_surplus = total_salary_surplus * proportion

        line.mobilization_bonus = self._calculate_mobilization(line.salary_surplus)
        line.extra_hours_value = self._calculate_extra_hours(line.salary_surplus)
        line.extra_hours_qty = self._calculate_extra_hours_qty(line.extra_hours_value, line.field_worker)
        line.thirteenth_bonus = self._calculate_thirteenth_bonus(
            daily_wage * proportion, 
            line.extra_hours_value, 
            is_weekend
        )
        line.fourteenth_bonus = self._calculate_fourteenth_bonus(line.field_worker) * proportion
        line.integral_bonus = line.integral_bonus * proportion

        line.save()

class WeekLevelCalculator(BasePayrollCalculator):
    """Calculate proportional bonuses for same-week worker lines"""
    
    def calculate(self, context: Dict[str, Any]) -> None:
        worker = context['worker']
        payroll_batch = context['payroll_batch']

        self._calculate_weekly_integral_for_worker(worker, payroll_batch)
    
    def _calculate_weekly_integral_for_worker(self, worker, payroll_batch):
        # Clear all integral bonuses
        self._clear_integral_bonuses(worker, payroll_batch)

        # Get worked days
        worked_days = self._get_worked_days(worker, payroll_batch)
        integral_bonus = self._calculate_integral_bonus(worker, worked_days)
        if integral_bonus > 0:
            self._distribute_integral_bonus(worker, payroll_batch, integral_bonus, worked_days)
    
    def _clear_integral_bonuses(self, worker, payroll_batch):
        PayrollBatchLine.objects.filter(
            field_worker=worker,
            payroll_batch=payroll_batch,
        ).update(integral_bonus=0)
    
    def _get_worked_days(self, worker, payroll_batch):
        return PayrollBatchLine.objects.filter(
            field_worker=worker,
            payroll_batch=payroll_batch,
            activity__labor_type__calculates_integral=True 
        ).values_list('date', flat=True).distinct().count()
    
    def _calculate_integral_bonus(self, worker_wage, worked_days):
        worker_daily_wage = self._get_daily_wage(worker_wage)
        if worked_days >= 5:
            return worker_daily_wage * 2
        elif worked_days == 4:
            return worker_daily_wage 
        else:
            return Decimal(0)
    
    def _distribute_integral_bonus(self, worker, payroll_batch, integral_bonus, worked_days):
        distributed_integral_bonus = Decimal(integral_bonus / worked_days)

        PayrollBatchLine.objects.filter(
            field_worker=worker,
            payroll_batch=payroll_batch,
            activity__labor_type__calculates_integral=True 
        ).update(integral_bonus=distributed_integral_bonus)
    
        


    

