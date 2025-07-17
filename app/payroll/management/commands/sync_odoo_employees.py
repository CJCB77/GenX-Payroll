"""
Script we invoke to sync the field workers 
from odoo through manage.py
"""
from django.core.management.base import BaseCommand
from payroll.models import FieldWorker
from core.services import get_field_workers, get_employee_contract
from django.utils import timezone
from logging import getLogger

logger = getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        total = 0
        for employee in get_field_workers():
            contract = get_employee_contract(employee["odoo_contract_id"]) or {}
            logger.info(f"Contract: {contract}")


            defaults = {
                "name": employee["name"],
                "mobile_phone": employee["mobile_phone"],
                "email": employee["email"],
                "identification_number": employee["identification_number"],
                # Contract fields
                "wage": contract.get("wage", 0.0),
                "start_date": contract.get("start_date", None),
                "end_date": contract.get("end_date", None),
                "contract_status": contract.get("contract_status", None),
            }
            field_worker, created = FieldWorker.objects.update_or_create(
                odoo_employee_id=employee["odoo_employee_id"],
                odoo_contract_id=employee["odoo_contract_id"],
                defaults=defaults,
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(f"{verb} {field_worker}")
            total += 1
        
        self.stdout.write(f"Synced {total} field workers")