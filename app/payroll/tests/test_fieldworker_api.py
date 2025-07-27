from django.urls import reverse
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APITestCase
from rest_framework import status
from core.tests import AuthenticatedAPITestCase
from payroll.models import (
    FieldWorker
)
from datetime import datetime, timedelta
import pytz

import logging

logger = logging.getLogger(__name__)

class PublicFieldWorkerApiTests(APITestCase):
    def setUp(self):
        self.list_url = reverse("payroll:fieldworker-list")

    def test_unathenticated_users_cannot_list_fieldworkers(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)       

class PrivateFieldWorkerApiTests(AuthenticatedAPITestCase):
    def _get_detail_url(self, pk):
        return reverse("payroll:fieldworker-detail", kwargs={"pk": pk})

    def setUp(self):
        super().setUp()
        self.list_url = reverse("payroll:fieldworker-list")
        
        FieldWorker.objects.bulk_create([
            FieldWorker(
                name="John Doe",
                odoo_contract_id=1,
                odoo_employee_id=1,
                identification_number="1234567899",
                wage=600.00,
                start_date="2023-01-01",
                end_date=None,
                contract_status="open",
                last_sync=datetime.now(pytz.UTC) - timedelta(days=1),
            ),
            FieldWorker(
                name="Jane Doe",
                odoo_contract_id=2,
                odoo_employee_id=2,
                identification_number="9876543210",
                wage=700.00,
                start_date="2023-01-01",
                end_date=None,
                contract_status="open",
                last_sync=datetime.now(pytz.UTC) - timedelta(days=1),
            ),
            FieldWorker(
                name="Michael Smith",
                odoo_contract_id=3,
                odoo_employee_id=3,
                identification_number="1236543210",
                wage=480.00,
                start_date="2023-01-01",
                end_date=None,
                contract_status="open",
                last_sync=datetime.now(pytz.UTC),
                is_active=False
            ),
        ])

    def test_list_defaults_to_actives_by_default(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 2)
        self.assertEqual(res.data["results"][0]["name"], "John Doe")
        self.assertEqual(res.data["results"][1]["name"], "Jane Doe")

    def test_include_inactive_query_param(self):
        res = self.client.get(f"{self.list_url}?include_inactive=true")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 3)
        names = [fw["name"] for fw in res.data["results"]]
        self.assertListEqual(names, ["John Doe", "Jane Doe", "Michael Smith"])

    def test_get_field_worker_odoo_id(self):
        res = self.client.get(f"{self.list_url}?odoo_employee_id=1")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["name"], "John Doe")

    def test_get_field_worker_by_name_match(self):
        res = self.client.get(f"{self.list_url}?name=Doe")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 2)
        names = [fw["name"] for fw in res.data["results"]]
        self.assertListEqual(names, ["John Doe", "Jane Doe"])

    def test_get_field_worker_by_contract_id(self):
        res = self.client.get(f"{self.list_url}?odoo_contract_id=1")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["name"], "John Doe")

    def test_cache_headers_present(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIsNotNone(res.headers["Cache-Control"])
        self.assertIn("max-age=900", res.headers["Cache-Control"])

    def test_pagination_keys_present(self):
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        for key in ('count', 'next', 'previous', 'results'):
            self.assertIn(key, data, f"{key} missing from response")
    
    def test_cache_hit_skips_db(self):
        # Warm the cache
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(self.list_url)
        self.assertEqual(len(ctx.captured_queries), 1)

        with CaptureQueriesContext(connection) as ctx:
            self.client.get(self.list_url)
        self.assertLess(len(ctx.captured_queries), 2)
    
    def test_single_field_worker_retrieve(self):
        # Create a worker
        field_worker = FieldWorker.objects.create(
            name="Tom holland",
            odoo_contract_id=5,
            odoo_employee_id=5,
            identification_number="1231202832",
            wage=600.00,
            start_date="2023-01-01",
            end_date=None,
            contract_status="open",
            last_sync=datetime.now(pytz.UTC) - timedelta(days=1),
        )
        detail_url = self._get_detail_url(field_worker.pk)
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], field_worker.name)
        self.assertEqual(res.data["odoo_contract_id"], field_worker.odoo_contract_id)
        self.assertEqual(res.data["odoo_employee_id"], field_worker.odoo_employee_id)
        self.assertEqual(res.data["identification_number"], field_worker.identification_number)
    
    def test_404_if_field_worker_does_not_exist(self):
        url = self._get_detail_url(9999)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)