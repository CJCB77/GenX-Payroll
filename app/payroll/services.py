from decimal import Decimal
from .models import (
    PayrollBatchLine,
    FieldWorker, 
    Tariff,
    PayrollConfiguration
)

def compute_line_totals(line: PayrollBatchLine):
    worker = line.field_worker
    daily_wage = worker.wage / Decimal(30)

    tariff_price = Tariff.objects.get(activity= line.activity, farm = line.payroll_batch.farm)
    total_cost = line.quantity * tariff_price.cost_per_unit
    surplus = max(Decimal(0), total_cost - daily_wage)

    return total_cost, surplus
    