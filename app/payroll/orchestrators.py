from django.db import transaction
from .calculators import InlineCalculator, DayLevelCalculator, WeekLevelCalculator
from .models import PayrollBatchLine

class PayrollCalculationOrchestrator:
    """
    Orchestrates the calculation flow
    """

    def __init__(self):
        self.inline_calculator = InlineCalculator()
        self.day_calculator = DayLevelCalculator()
        self.week_calculator = WeekLevelCalculator()
    
    @transaction.atomic
    def recalculate_line(self, line_id:int, recalc_week:bool=True) -> None:
        """Main entry point for line recalculation"""
        line = PayrollBatchLine.objects.select_related(
            'field_worker',
            'payroll_batch',
            'activity'
        ).get(id=line_id)

        # Step 1: Inline calculations
        self.inline_calculator.calculate({
            'line': line
        })

        # Step 2: Day-level recalculation if needed
        if self._needs_day_recalculation(line):
            self._apply_day_calculations(line)

        # Step 3: Week-level recalculation if needed
        if recalc_week:
            self._apply_week_recalculation(line)
    
    def _needs_day_recalculation(self, line) -> bool:
        return PayrollBatchLine.objects.filter(
            field_worker=line.field_worker,
            payroll_batch=line.payroll_batch,
            date=line.date
        ).count() > 1

    def _apply_day_calculations(self, line):
        self.day_calculator.calculate({
            'worker': line.field_worker,
            'payroll_batch': line.payroll_batch,
            'date': line.date
        })
    
    def _apply_week_recalculation(self, line):
        self.week_calculator.calculate({
            'worker': line.field_worker,
            'payroll_batch': line.payroll_batch
        })
    
    @transaction.atomic
    def recalculate_after_deletion(self, worker, payroll_batch, date):
        """Recalculate after a line is deleted"""
        # Recalculate day porportions for remaining lines
        self.day_calculator.calculate({
            'worker': worker,
            'payroll_batch': payroll_batch,
            'date': date
        })

        # Recalculate week bonuses
        self.week_calculator.calculate({
            'worker': worker,
            'payroll_batch': payroll_batch
        })