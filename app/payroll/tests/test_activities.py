from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from payroll.models import (
    ActivityGroup, 
    Activity,
    Uom,
    LaborType
)
from core.tests import AuthenticatedAPITestCase

import logging

logger = logging.getLogger(__name__)

class PublicActivityAPITestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.list_url = reverse("payroll:activity-list")

    def test_unauthenticated_activity_list(self):
        res = self.client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class PrivateActivityAPITestCase(AuthenticatedAPITestCase):

    def _get_activity_group_detail_url(self, pk):
        return reverse("payroll:activity-group-detail", args=[pk])

    def _get_activity_detail_url(self, pk):
        return reverse("payroll:activity-detail", args=[pk])

    def setUp(self):
        super().setUp()
        self.group_list_url = reverse("payroll:activity-group-list")
        self.activity_list_url = reverse("payroll:activity-list")

        self.labor_type1 = LaborType.objects.create(name="Test Labor Type", code="TLT")
        self.labor_type2 = LaborType.objects.create(name="Test Labor Type 2", code="TLT2")
        self.uom1 = Uom.objects.create(name="Test UOM")
        self.uom2 = Uom.objects.create(name="Test UOM 2")
        self.activity_group = ActivityGroup.objects.create(name="Test Activity Group")

    def test_create_activity_group(self):
        """
        Ensure we can create a new activity group.
        """
        payload = {
            "name":"Test Activity Group 2",
            "code":"TSTAG2",
            "description":"Test Activity Group 2 Description"
        }
        res = self.client.post(self.group_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertTrue(ActivityGroup.objects.filter(code="TSTAG2").exists())
        self.assertIn("id", res.data)
        self.assertEqual(res.data["name"], "Test Activity Group 2")
    
    def test_list_activity_group(self):
        ActivityGroup.objects.create(
            name="Test Activity Group 2", 
            code="TSTAG2", 
            description="Test Activity Group 2 Description"
        )

        res = self.client.get(self.group_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

        names = [ag["name"] for ag in res.data["results"]]
        self.assertListEqual(names, ["Test Activity Group", "Test Activity Group 2"])
    
    def test_retrieve_activity_group(self):
        activity_group = ActivityGroup.objects.create(
            name="Test Activity Group 2", 
            code="TSTAG2", 
            description="Test Activity Group 2 Description"
        )

        detail_url = self._get_activity_group_detail_url(activity_group.pk)

        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], "Test Activity Group 2")
        self.assertEqual(res.data["code"], "TSTAG2")
        self.assertEqual(res.data["description"], "Test Activity Group 2 Description")
    
    def test_update_activity_group(self):
        activity_group = ActivityGroup.objects.create(
            name="Test Activity Group 2", 
            code="TSTAG2", 
            description="Test Activity Group 2 Description"
        )

        detail_url = self._get_activity_group_detail_url(activity_group.pk)

        payload = {
            "name":"Test Activity Group 3",
            "code":"TSTAG3",
            "description":"Test Activity Group 3 Description"
        }
        res = self.client.put(detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        activity_group.refresh_from_db()
        self.assertEqual(activity_group.name, "Test Activity Group 3")
        self.assertEqual(activity_group.code, "TSTAG3")
        self.assertEqual(activity_group.description, "Test Activity Group 3 Description")
    
    def test_delete_activity_group(self):
        activity_group = ActivityGroup.objects.create(
            name="Test Activity Group 2", 
            code="TSTAG2", 
            description="Test Activity Group 2 Description"
        )

        detail_url = self._get_activity_group_detail_url(activity_group.pk)

        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ActivityGroup.objects.filter(pk=activity_group.pk).exists())

    def test_create_activity(self):
        payload = {
            "name":"Test Activity 1",
            "activity_group": self.activity_group.pk,
            "labor_type": self.labor_type1.pk,
            "uom": self.uom1.pk
        }
        res = self.client.post(self.activity_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Activity.objects.filter(name="Test Activity 1").exists())
        self.assertIn("id", res.data)
        self.assertEqual(res.data["name"], "Test Activity 1")
    
    def test_list_activity(self):
        Activity.objects.bulk_create([
            Activity(
                name="Test Activity 1", 
                activity_group=self.activity_group, 
                labor_type=self.labor_type1, 
                uom=self.uom1),
            Activity(
                name="Test Activity 2", 
                activity_group=self.activity_group, 
                labor_type=self.labor_type2, 
                uom=self.uom2),
            Activity(
                name="Test Activity 3", 
                activity_group=self.activity_group, 
                labor_type=self.labor_type1, 
                uom=self.uom1),
        ])

        res = self.client.get(self.activity_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 3)

        names = [ag["name"] for ag in res.data["results"]]
        self.assertListEqual(names, ["Test Activity 1", "Test Activity 2", "Test Activity 3"])
    
    def test_retrieve_activity(self):
        activity = Activity.objects.create(
            name="Test Activity 1", 
            activity_group=self.activity_group,
            labor_type=self.labor_type1,
            uom=self.uom1
        )

        detail_url = self._get_activity_detail_url(activity.pk)

        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["name"], "Test Activity 1")
        self.assertEqual(res.data["activity_group"]['name'], self.activity_group.name)
    
    def test_update_activity(self):
        activity = Activity.objects.create(
            name="Test Activity 1", 
            activity_group=self.activity_group,
            labor_type=self.labor_type1,
            uom=self.uom1
        )

        detail_url = self._get_activity_detail_url(activity.pk)

        payload = {
            "name":"Test Activity 2",
        }
        res = self.client.patch(detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        activity.refresh_from_db()
        self.assertEqual(activity.name, "Test Activity 2")
    
    def test_delete_activity(self):
        activity = Activity.objects.create(
            name="Test Activity 1", 
            activity_group=self.activity_group,
            labor_type=self.labor_type1,
            uom=self.uom1
        )

        detail_url = self._get_activity_detail_url(activity.pk)

        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Activity.objects.filter(pk=activity.pk).exists())
    
    def test_filter_activities_by_group(self):
        ActivityGroup.objects.create(
            name="Test Activity Group 2", 
            code="TSTAG2", 
        )
        Activity.objects.bulk_create([
            Activity(
                name="Test Activity 1", 
                activity_group=self.activity_group,
                labor_type=self.labor_type1,
                uom=self.uom1
            ),
            Activity(
                name="Test Activity 2", 
                activity_group=self.activity_group,
                labor_type=self.labor_type2,
                uom=self.uom2
            ),
            Activity(
                name="Test Activity 3", 
                activity_group=ActivityGroup.objects.get(code="TSTAG2"),
                labor_type=self.labor_type1,
                uom=self.uom1
            ),
        ])

        res = self.client.get(self.activity_list_url + "?activity_group=" + str(self.activity_group.pk))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 2)

        names = [ag["name"] for ag in res.data["results"]]
        self.assertListEqual(names, ["Test Activity 1", "Test Activity 2"])
    
    def test_filter_activities_by_labor_type(self):
        Activity.objects.bulk_create([
            Activity(
                name="Test Activity 1", 
                activity_group=self.activity_group,
                labor_type=self.labor_type1,
                uom=self.uom1
            ),
            Activity(
                name="Test Activity 2", 
                activity_group=self.activity_group,
                labor_type=self.labor_type2,
                uom=self.uom2
            ),
        ])

        res = self.client.get(self.activity_list_url + "?labor_type=" + str(self.labor_type1.pk))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

        names = [ag["name"] for ag in res.data["results"]]
        self.assertListEqual(names, ["Test Activity 1"])
    
    def test_filter_activities_by_uom(self):
        Activity.objects.bulk_create([
            Activity(
                name="Test Activity 1", 
                activity_group=self.activity_group,
                labor_type=self.labor_type1,
                uom=self.uom1
            ),
            Activity(
                name="Test Activity 2", 
                activity_group=self.activity_group,
                labor_type=self.labor_type2,
                uom=self.uom2
            ),
        ])

        res = self.client.get(self.activity_list_url + "?uom=" + str(self.uom1.pk))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

        names = [ag["name"] for ag in res.data["results"]]
        self.assertListEqual(names, ["Test Activity 1"])