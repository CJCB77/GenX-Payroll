from django.utils import timezone
from django.db import transaction
from celery import shared_task
from logging import getLogger
from .models import FieldWorker
from datetime import datetime
from .services import (
    compute_line_totals
)

from payroll.models import (
    PayrollBatchLine
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

def recalc_single_line(line_id):
    """
    Called on create or update of a line: recomputes costs, bonuses, etc
    """
    line = PayrollBatchLine.objects.get(id=line_id)
    # Get totals
    cost, surplus = compute_line_totals(line)
    logger.info(f"Cost: {cost}, Surplus: {surplus}")
    line.total_cost = cost
    line.salary_surplus = surplus
    # # Get mobilization and extra hours
    # mobilization, extra_hours, extra_hours_qty = compute_mobilization_and_extra_hours(line)
    # line.mobilization_bonus = mobilization
    # line.extra_hours_value = extra_hours
    # line.extra_hours_qty = extra_hours_qty

    # # Get social benefits
    # line.thirteenth_bonus = compute_thirteenth_bonus(line)
    # line.fourteenth_bonus = compute_fourteenth_bonus(line)
    line.save()