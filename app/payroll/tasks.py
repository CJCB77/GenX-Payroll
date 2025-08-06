from collections import defaultdict
from typing import List
from django.utils import timezone
from django.db import transaction
from django.core.files.storage import default_storage
from celery import shared_task, group, chain
from logging import getLogger
from datetime import datetime
from .orchestrators import PayrollCalculationOrchestrator
from payroll.models import (
    PayrollBatchLine,
    PayrollBatch,
    FieldWorker,
)
from payroll.payroll_processor import (
    PayrollBatchCreator,
    PayrollFileProcessor,
    PayrollFileValidator,
    ValidationError
)
from payroll.calculators import (
    DayLevelCalculator,
    InlineCalculator,
    WeekLevelCalculator
)

logger = getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_employee(self, payload):
    logger.info(f"Received a payload: {payload}")
    try:
        action = payload.get("action", "create")
        employee_id = payload.get("id")
        update_timestamp = payload.get("timestamp")

        # Convert timestamp if provided
        if update_timestamp and isinstance(update_timestamp, str):
            update_timestamp = datetime.fromisoformat(update_timestamp.replace('Z', '+00:00'))
        else:
            update_timestamp = timezone.now()

        employee_data = {
            "name": payload["name"],
            "email": payload["email"],
            "mobile_phone": payload["mobile_phone"],
            "identification_number": payload["identification_number"],
            "odoo_contract_id": payload["contract_id"],
            "wage": payload["wage"],
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
            "contract_status": payload["contract_status"],
            "last_sync": update_timestamp
        }

        if action in ["update", "create"]:
            with transaction.atomic():
                field_worker, created =FieldWorker.objects.get_or_create(
                    odoo_employee_id = employee_id,
                    defaults=employee_data
                )
                if not created and field_worker.last_sync < update_timestamp:
                    for k, v in employee_data.items():
                        setattr(field_worker, k, v)
                    field_worker.save()
                    logger.info(f"Updated field worker: {field_worker}")
                elif created:
                    logger.info(f"Created field worker: {field_worker}")
                else:
                    logger.info(f"Field worker already exists and is up to date: {field_worker}")

    except KeyError as e:
        msg = f"Missing required fields in payload: {e}"
        logger.error(msg)
        raise self.retry(exc=KeyError(msg))
    except Exception as e:
        msg = f"Error syncing employee: {e}"
        logger.error(msg)
        raise self.retry(exc=Exception(msg))
    
@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_contract(self, payload):
    logger.info(f"Received a payload: {payload}")
    try:
        action = payload.get("action")
        contract_id = payload.get("contract_id")
        # Get timestamp
        update_timestamp = payload.get("timestamp")
        if not update_timestamp:
            # Fallback to current timestamp
            update_timestamp = timezone.now().isoformat()
            logger.warning(f"Timestamp not found in payload, using current timestamp: {update_timestamp}")

        if isinstance(update_timestamp, str):
            update_timestamp = datetime.fromisoformat(update_timestamp.replace("Z", "+00:00"))

        contract_data = {
            "wage": payload["wage"],
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
            "contract_status": payload["contract_status"],
        }

        if action == "update":
            with transaction.atomic():
                # Use select_for_update() to lock the row for update
                field_workers = FieldWorker.objects.select_for_update().filter(odoo_contract_id=contract_id)
                count = field_workers.count()

                if count == 0:
                    logger.warning(f"No field worker found for contract_id: {contract_id}")
                    return

                elif count > 1:
                    logger.warning(f"Multiple field workers found for contract_id: {contract_id}")
                    for field_worker in field_workers:
                        if not field_worker.last_sync or update_timestamp > field_worker.last_sync:
                            field_worker.wage = contract_data["wage"]
                            field_worker.start_date = contract_data["start_date"]
                            field_worker.end_date = contract_data["end_date"]
                            field_worker.contract_status = contract_data["contract_status"]
                            field_worker.last_sync = timezone.now()
                            field_worker.save()
                            logger.info(f"Updated field worker: {field_worker}")
                        else:
                            logger.info(f"Skipping - field worker already synced: {field_worker}")
                else:
                    # Single field worker - normal case
                    field_worker = field_workers[0]
                    if not field_worker.last_sync or update_timestamp > field_worker.last_sync:
                        field_worker.wage = contract_data["wage"]
                        field_worker.start_date = contract_data["start_date"]
                        field_worker.end_date = contract_data["end_date"]
                        field_worker.contract_status = contract_data["contract_status"]
                        field_worker.last_sync = timezone.now()
                        field_worker.save()
                        logger.info(f"Updated field worker: {field_worker}")
                    else:
                        logger.info(f"Field worker already synced: {field_worker}")
            
    except KeyError as e:
        logger.error(f"Missing required fields in payload: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing employee: {e}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3)
def recalc_line_task(self, line_id, recalc_week=True):
    """
    Recalculate one line (and optionally its week).
    When done, mark the batch 'ready'.
    """
    orchestrator = PayrollCalculationOrchestrator()
    orchestrator.recalculate_line(line_id, recalc_week=recalc_week)

    # finally mark batch ready
    batch_id = PayrollBatchLine.objects.get(pk=line_id).payroll_batch_id
    PayrollBatch.objects.filter(pk=batch_id).update(
        status='ready',
    )

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def recalc_delete_task(self, worker_id, batch_id, date_iso):
    """
    Recalculate day + week after a deletion.
    Then mark the batch 'ready'.
    """
    from datetime import date
    y, m, d = map(int, date_iso.split('-'))
    dt = date(y, m, d)

    worker = FieldWorker.objects.get(pk=worker_id)
    batch  = PayrollBatch.objects.get(pk=batch_id)

    orchestrator = PayrollCalculationOrchestrator()
    orchestrator.recalculate_after_deletion(worker, batch, dt)

    batch.status = 'ready'
    batch.save(update_fields=['status'])

@shared_task
def batch_inline_calculation_task(batch_id):
    """
    Task that calculates inline fields for all lines in a batch
    """
    try:
        lines = PayrollBatchLine.objects.filter(payroll_batch__id=batch_id)
        calculator = InlineCalculator()

        calculator.calculate_batch(lines)
        
        logger.info(f"Calculated inline fields for {lines.count()} lines in batch {batch_id}")
        return batch_id
    
    except Exception as e:
        logger.error(f"Error calculating inline fields for batch {batch_id}: {e}")
        raise

@shared_task
def batch_day_level_calculation_task(batch_id):
    """
    Task to calculate day-level proportional bonuses
    Groups by (worker, date) and distributes proportionally
    """
    try:
        day_groups = defaultdict(list)
        lines = PayrollBatchLine.objects.filter(payroll_batch__id=batch_id).select_related('field_worker')

        for line in lines:
            key = (line.field_worker.id, line.date)
            day_groups[key].append(line)
        
        # Filter to only groups with multiple lines per day
        multi_line_days = {k: v for k, v in day_groups.items() if len(v) > 1}

        calculator = DayLevelCalculator()

        for (worker_id, date), lines_for_day in multi_line_days.items():
            worker = lines_for_day[0].field_worker
            context = {'worker': worker, 'payroll_batch': batch_id, 'date': date}
            calculator.calculate(context)

        logger.info(f"Calculated day-level proportional bonuses for {len(multi_line_days)} days in batch {batch_id}")
        return batch_id

    except Exception as e:
        logger.error(f"Error calculating day-level proportional bonuses for batch {batch_id}: {e}")
        raise

@shared_task
def batch_week_level_calculation_task(batch_id):
    """
    Task to calculate week-level proportional bonuses
    Groups by worker and calculates weekly
    """
    try:
        payroll_batch = PayrollBatch.objects.get(pk=batch_id)
        lines_by_worker = PayrollBatchLine.objects.filter(payroll_batch=payroll_batch)\
            .order_by('field_worker')\
            .distinct('field_worker')

        calculator = WeekLevelCalculator()

        for line in lines_by_worker:
            context = {'worker': line.field_worker, 'payroll_batch': batch_id}
            calculator.calculate(context)

        logger.info(f"Calculated week-level proportional bonuses for {lines_by_worker.count()} workers in batch {batch_id}")
        return batch_id

    except Exception as e:
        logger.error(f"Error calculating week-level proportional bonuses for batch {batch_id}: {e}")
        raise


@shared_task
def finalize_batch_task(batch_id):
    try:
        PayrollBatch.objects.filter(pk=batch_id).update(status='ready', error_message=None)

    except Exception as e:
        logger.error(f"Error finalizing batch {batch_id}: {e}")
        raise

@shared_task
def import_payroll_file(batch_id, temp_path):
    """Main task for importing payroll files"""
    batch = PayrollBatch.objects.get(pk=batch_id)
    full_path = default_storage.path(temp_path)

    try:
        # Read and clean file
        processor = PayrollFileProcessor()
        df = processor.read_file(full_path)
        df = processor.clean_data(df)

        # Validate file
        validator = PayrollFileValidator()

        structure_errors = validator.validate_structure(df)
        if structure_errors:
            _handle_batch_error(batch, structure_errors)
            return

        # Create batch lines

        batch_creator = PayrollBatchCreator()
        batch_creator._create_batch_lines(batch, df)

        # Chain calculation tasks efficiently
        calculation_chain = chain(
            batch_inline_calculation_task.s(batch_id),
            batch_day_level_calculation_task.s(),
            batch_week_level_calculation_task.s(),
            finalize_batch_task.s()
        )

        calculation_chain.apply_async()

        logger.info(f"Started calculation tasks for batch {batch_id}")

    except Exception as e:
        logger.error(f"Error importing payroll file for batch {batch_id}: {e}")
        batch.status = 'error'
        batch.error_message = str(e)
        batch.save(update_fields=['status', 'error_message'])
        raise
    finally:
        # Delete temp file
        default_storage.delete(temp_path)

def _handle_batch_error(batch: PayrollBatch, errors: List[ValidationError]) -> None:
    """Handle validation errors by updating batch status"""
    error_msg = "; ".join(str(error) for error in errors[:10])  # Limit error message length
    if len(errors) > 10:
        error_msg += f"; ... and {len(errors) - 10} more errors"
    
    batch.status = 'error'
    batch.error_message = error_msg  # Assuming you have this field
    batch.save(update_fields=['status', 'error_message'])
