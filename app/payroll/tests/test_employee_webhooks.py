"""
Tests for the employee webhooks
"""
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from payroll.models import FieldWorker
from payroll.tasks import sync_employee

import pytz
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

EMPLOYEE_HOOK_URL = reverse("payroll:hook-employee")
CONTRACT_HOOK_URL = reverse("payroll:hook-contract")

@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class EmployeeWebhooksTests(APITestCase):
    def setUp(self):
        # We could set API headers here
        pass

    def create_employee_payload(self, action="create", ts=None, **overrides):
        now = ts or datetime.now(pytz.UTC)
        base = {
            "id":99,
            "name": "John Doe",
            "mobile_phone": "123456789",
            "email": "jdoe@me.com",
            "identification_number": "1234567899",
            "contract_id": 777,
            "wage": 600.00,
            "start_date": "2023-01-01",
            "end_date": None,
            "contract_status": "open",
            "action": action,
            "timestamp": now.isoformat(),
        }
        base.update(overrides)
        return base

    def test_sync_employee_creates_a_field_worker(self):
        payload = self.create_employee_payload()
        logger.info(f"Payload: {payload}")

        res = self.client.post(EMPLOYEE_HOOK_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        fw = FieldWorker.objects.get(odoo_employee_id=payload["id"])
        self.assertEqual(fw.name, payload["name"])
        self.assertEqual(fw.wage, payload["wage"])
        self.assertEqual(fw.start_date.isoformat(), payload["start_date"])
        self.assertEqual(fw.end_date, payload["end_date"])
        self.assertEqual(fw.contract_status, payload["contract_status"])
        self.assertIsNotNone(fw.last_sync)

    def test_sync_employee_updates_a_field_worker(self):
        old_ts = datetime.now(pytz.UTC) - timedelta(days=1)
        fw = FieldWorker.objects.create(
            name="John Doe",
            odoo_employee_id=99,
            identification_number="1234567899",
            last_sync=old_ts,
            wage=600.00,
            end_date=None,
            contract_status="new",
        )

        # Send an update with a newer timestamp
        new_ts = datetime.now(pytz.UTC)
        payload = self.create_employee_payload(
            action="update", 
            timestamp=new_ts,
            name="Johnny Doe",
            wage=700.00,
            contract_status="open",
        )
        res = self.client.post(EMPLOYEE_HOOK_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        fw.refresh_from_db()
        fw = FieldWorker.objects.get(odoo_employee_id=payload["id"])
        self.assertEqual(fw.name, payload["name"])
        self.assertEqual(fw.wage, payload["wage"])
        self.assertEqual(fw.email, "jdoe@me.com")
        self.assertTrue(fw.last_sync > old_ts)
    
    def test_sync_employee_skips_if_payload_older_than_last_sync(self):
        """
        If the payload timestamp is older than the last sync timestamp,
        the record should not be updated
        """
        old_ts = datetime.now(pytz.UTC) - timedelta(days=1)
        fw = FieldWorker.objects.create(
            name="John Doe",
            odoo_employee_id=99,
            identification_number="1234567899",
            last_sync=datetime.now(pytz.UTC),
            wage=600.00,
            end_date=None,
            contract_status="new",
        )
        
        # Send an update wiht an older timestamp
        payload = self.create_employee_payload(
            action="update", 
            timestamp=old_ts,
            name="Johnny Doe",
            wage=700.00,
            contract_status="open",
        )
        res = self.client.post(EMPLOYEE_HOOK_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        fw.refresh_from_db()
        self.assertEqual(fw.name, "John Doe")
        self.assertEqual(str(fw.wage), "600.00")


    def test_sync_employee_missing_required_key_triggers_retry(self):
        """
        If key data is missing, the task will raise a Retry exception
        """
        bad_payload = {
            "action": "create",
            "odoo_employee_id": 999,
        } # missing required keys
        with self.assertRaises(Exception) as e:
            # Because of CELERY_TASK_ALWAYS_EAGER=True, this will raise
            sync_employee(bad_payload)

        self.assertIn("Missing required fields", str(e.exception))
