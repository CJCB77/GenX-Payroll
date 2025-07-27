from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import (
    Farm, 
    Tariff, 
    ActivityGroup, 
    Activity,
    LaborType,
    Uom
)
from core.tests import AuthenticatedAPITestCase
from decimal import Decimal

import logging

logger = logging.getLogger(__name__)

class PublicFarmApiTests(APITestCase):
    def setUp(self):
        self.list_url = reverse("payroll:farm-list")

    def test_unauthenticated_farm_list(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class PrivateFarmApiTests(AuthenticatedAPITestCase):
    def _get_farm_detail_url(self, pk):
        return reverse("payroll:farm-detail", kwargs={"pk": pk})

    def _create_default_farm(self, **override):
        return Farm.objects.create(
            name="Test Farm",
            code="TSTF",
            description="Test Farm Description",
            **override
        )

    def setUp(self):
        super().setUp()
        self.login_url = reverse("user:login")
        self.list_url = reverse("payroll:farm-list")    

    def test_create_farm(self):
        payload = {
            "name":"Test Farm",
            "code":"TSTF",
            "description":"Test Farm Description"
        }
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Farm.objects.filter(code="TSTF").exists())
        self.assertIn("id", res.data)
        self.assertEqual(res.data["name"], "Test Farm")
    
    def test_retrieve_farm(self):
        farm = self._create_default_farm()
        detail_url = self._get_farm_detail_url(farm.pk)

        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], "Test Farm")
        self.assertEqual(res.data["code"], "TSTF")
        self.assertEqual(res.data["description"], "Test Farm Description")
    
    def test_patch_farm(self):
        farm = self._create_default_farm()
        detail_url = self._get_farm_detail_url(farm.pk)

        payload = {
            "name":"Modified Farm",
        }
        res = self.client.patch(detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], "Modified Farm")
        self.assertEqual(res.data["code"], "TSTF")
        # Verify persistence
        farm.refresh_from_db()
        self.assertEqual(farm.name, "Modified Farm")
    
    def test_delete_farm(self):
        farm = self._create_default_farm()
        detail_url = self._get_farm_detail_url(farm.pk)

        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Farm.objects.filter(pk=farm.pk).exists())
    
    def test_list_retrieval_after_creation(self):
        Farm.objects.bulk_create([
            Farm(name="Test Farm 1", code="TSTF1", description="Test Farm 1 Description"),
            Farm(name="Test Farm 2", code="TSTF2", description="Test Farm 2 Description"),
            Farm(name="Test Farm 3", code="TSTF3", description="Test Farm 3 Description")
        ])

        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 3)

        names = [fw["name"] for fw in res.data["results"]]
        self.assertListEqual(names, ["Test Farm 1", "Test Farm 2", "Test Farm 3"])

class TariffApiTests(AuthenticatedAPITestCase):
    def _get_tariff_detail_url(self, pk):
        return reverse("payroll:tariff-detail", kwargs={"pk": pk})
    
    def setUp(self):
        super().setUp()
        self.activity_group = ActivityGroup.objects.create(
            name="Test Activity Group", 
            code="TSTAG", 
            description="Test Activity Group Description"
        )
        self.labor_type = LaborType.objects.create(
            name="Test Labor Type", 
            code="TLT"
        )
        self.uom = Uom.objects.create(
            name="Test UOM"
        )
        self.activity = Activity.objects.create(
            name="Harvest", 
            activity_group=self.activity_group,
            labor_type=self.labor_type,
            uom=self.uom
        )
        self.activity2 = Activity.objects.create(
            name="Plant", 
            activity_group=self.activity_group,
            labor_type=self.labor_type,
            uom=self.uom
        )
        self.farm1 = Farm.objects.create(
            name="Test Farm 1", 
            code="TSTF1", 
        )
        self.farm2 = Farm.objects.create(
            name="Test Farm 2", 
            code="TSTF2", 
        )

        # Seed some tariffs
        self.tariff1 = Tariff.objects.create(
            name="Test Tariff 1", 
            activity=self.activity,
            farm=self.farm1,
            cost_per_unit=10.00
        )
        self.tariff2 = Tariff.objects.create(
            name="Test Tariff 2", 
            activity=self.activity2,
            farm=self.farm2,
            cost_per_unit=20.00
        )

        self.list_url = reverse("payroll:tariff-list")
    
    def test_list_all_tariffs(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
    
    def test_filter_by_activity(self):
        res = self.client.get(self.list_url + f"?activity={self.activity.pk}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["name"], "Test Tariff 1")
    
    def test_filter_by_farm(self):
        res = self.client.get(self.list_url + f"?farm={self.farm1.pk}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["name"], "Test Tariff 1")
    
    def test_create_tariff(self):
        payload = {
            "name":"Test Tariff 3",
            "activity":self.activity.pk,
            "farm":self.farm2.pk,
            "cost_per_unit":30.00,
            "uom":self.uom.pk
        }
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Tariff.objects.filter(name="Test Tariff 3").exists())
        self.assertIn("id", res.data)
        self.assertEqual(res.data["name"], "Test Tariff 3")
    
    def test_unique_farm_activity_constraint(self):
        payload = {
            "name ":"Test Tariff 3",
            "activity":self.activity.pk,
            "farm":self.farm1.pk,
            "cost_per_unit":30.00,
            "uom":self.uom.pk
        }
        res = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_retrieve_tariff(self):
        detail_url = self._get_tariff_detail_url(self.tariff1.pk)

        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], "Test Tariff 1")
        self.assertEqual(res.data["farm"], self.farm1.pk)
        self.assertEqual(Decimal(res.data["cost_per_unit"]), Decimal(10.00))
    
    def test_patch_tariff(self):
        url = self._get_tariff_detail_url(self.tariff1.pk)

        payload = {
            "name":"Modified Tariff",
        }
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], "Modified Tariff")
        self.assertEqual(res.data["activity"], self.activity.pk)

    def test_delete_tariff(self):
        url = self._get_tariff_detail_url(self.tariff1.pk)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Tariff.objects.filter(pk=self.tariff1.pk).exists())
