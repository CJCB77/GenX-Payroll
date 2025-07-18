from celery import shared_task
from celery.utils.log import get_task_logger
from .models import FieldWorker

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_employee(self, payload):
    logger.info(f"Received a payload: {payload}")
    try:
        action = payload.get("action", "create")
        employee_id = payload.get("id")

        employee_data = {
            "name": payload["name"],
            "email": payload["email"],
            "mobile_phone": payload["mobile_phone"],
            "identification_number": payload["identification_number"],
            "odoo_contract_id": payload["contract_id"],
        }

        if action in ["update", "create"]:
            field_worker, created =FieldWorker.objects.update_or_create(
                odoo_employee_id = employee_id,
                defaults=employee_data
            )
            if created:
                logger.info(f"Created field worker: {field_worker}")
            else:
                logger.info(f"Updated field worker: {field_worker}")
    except KeyError as e:
        logger.error(f"Missing required fields in payload: {e}")
        raise self.retry(exc=e)
    except Exception as e:
        logger.error(f"Error syncing employee: {e}")
        raise self.retry(exc=e)