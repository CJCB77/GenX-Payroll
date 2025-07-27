from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from core.tests import AuthenticatedAPITestCase
from payroll.models import (
    PayrollConfiguration,
    PayrollBatch,
)
from decimal import Decimal

import logging

logger = logging.getLogger(__name__)

class PayrollConfigTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("payroll:configuration")

    def test_retrieve_default_config(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Defaults as defined in get_object()
        self.assertEqual(Decimal(res.data["mobilization_percentage"]), Decimal('0.00'))
        self.assertEqual(Decimal(res.data["extra_hours_percentage"]), Decimal('0.00'))
        self.assertEqual(Decimal(res.data["basic_monthly_wage"]), Decimal('0.00'))
    
    def test_patch_updates_config(self):
        PayrollConfiguration.objects.create(
            pk=1,
            mobilization_percentage=60,
            extra_hours_percentage=40,
            basic_monthly_wage=600
        )
        payload = {
            "basic_monthly_wage": 700
        }
        res = self.client.patch(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Defaults as defined in get_object()
        self.assertEqual(Decimal(Decimal(res.data["basic_monthly_wage"])), Decimal('700.00'))

        conf = PayrollConfiguration.objects.get(pk=1)
        self.assertEqual(Decimal(conf.basic_monthly_wage), Decimal('700.00'))
        self.assertEqual(Decimal(conf.mobilization_percentage), Decimal('60.00'))
        self.assertEqual(Decimal(conf.extra_hours_percentage), Decimal('40.00'))

class PayrollBatchApiTests(AuthenticatedAPITestCase):

    def _get_payroll_batch_detail_url(self, pk):
        return reverse("payroll:payroll-batch-detail", kwargs={"pk": pk})

    def setUp(self):
        super().setUp()
        self.list_url = reverse("payroll:payroll-batch-list")

        # Seed some batches with differen statuses
        self.pb1 = PayrollBatch.objects.create(
            name="Test Payroll Batch 1", 
            start_date = "2025-06-30",
            end_date = "2025-07-14",
            status="submitted",
        )
        self.pb2 = PayrollBatch.objects.create(
            name="Test Payroll Batch 2", 
            start_date = "2025-07-14",
            end_date = "2025-07-28",
        )
    
    def test_list_all_batches(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 2)
        self.assertEqual(res.data["results"][0]["name"], "Test Payroll Batch 1")
        self.assertEqual(res.data["results"][1]["name"], "Test Payroll Batch 2")
    
    def test_filter_by_status(self):
        res = self.client.get(self.list_url + "?status=submitted")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["name"], "Test Payroll Batch 1")
    
    def test_search_by_name(self):
        res = self.client.get(self.list_url + "?search=Test Payroll Batch 1")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["name"], "Test Payroll Batch 1")
    
    def test_create_batch(self):
        payload = {
            "name": "Test Payroll Batch 3",
            "start_date": "2025-08-01",
            "end_date": "2025-08-15",
        }
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertTrue(PayrollBatch.objects.filter(name="Test Payroll Batch 3").exists())
        self.assertIn("id", res.data)
        self.assertEqual(res.data["name"], "Test Payroll Batch 3")
    
    def test_retrieve_batch(self):
        detail_url = self._get_payroll_batch_detail_url(self.pb1.pk)

        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], "Test Payroll Batch 1")
        self.assertEqual(res.data["status"], "submitted")

    def test_update_batch(self):
        detail_url = self._get_payroll_batch_detail_url(self.pb1.pk)

        payload = {"status": "approved"}
        res = self.client.patch(detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["status"], "approved")
    
    def test_delete_branch(self):
        detail_url = self._get_payroll_batch_detail_url(self.pb1.pk)

        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(PayrollBatch.objects.filter(pk=self.pb1.pk).exists())