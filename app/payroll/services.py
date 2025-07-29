from decimal import Decimal
from .models import (
    PayrollBatchLine,
    FieldWorker, 
    Tariff,
    PayrollConfiguration
)
import logging

logger = logging.getLogger(__name__)

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

    return total_cost, surplus
    