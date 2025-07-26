from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import Farm
from core.tests import AuthenticatedAPITestCase

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