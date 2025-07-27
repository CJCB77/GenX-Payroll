from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from core.tests import AuthenticatedAPITestCase
from payroll.models import (
    PayrollConfiguration
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