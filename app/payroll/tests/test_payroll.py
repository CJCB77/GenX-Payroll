from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from core.tests import AuthenticatedAPITestCase
from payroll.models import (
    PayrollConfiguration,
    PayrollBatch,
    Farm,
    PayrollBatchLine,
    FieldWorker,
    Activity,
    Tariff,
    Uom,
    LaborType,
    ActivityGroup,
)
from decimal import Decimal
from datetime import date

import logging

logger = logging.getLogger(__name__)

DAYS_OF_THE_YEAR = 364
DAYS_OF_THE_MONTH = 30
MONTHS_IN_YEAR = 12

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
            basic_monthly_wage=600,
            extra_hour_multiplier=1.5
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
        self.farm = Farm.objects.create(
            name="Test Farm",
            code="TSTF",
        )

        # Seed some batches with differen statuses
        self.pb1 = PayrollBatch.objects.create(
            name="Test Payroll Batch 1", 
            start_date = date(2025, 7, 1),
            end_date = date(2025, 7, 14),
            status="submitted",
            farm=self.farm
        )
        self.pb2 = PayrollBatch.objects.create(
            name="Test Payroll Batch 2", 
            start_date = date(2025, 7, 15),
            end_date = date(2025, 7, 28),
            farm=self.farm
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
            "start_date": date(2025, 8, 1),
            "end_date": date(2025, 8, 14),
            "farm": self.farm.id,
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

class PayrollBatchLineAPITests(AuthenticatedAPITestCase):

    def _get_payroll_line_detail_url_by_batch(self, batch_pk, line_pk):
        return reverse(
            "payroll:payroll-line-detail", 
            kwargs={"batch_pk": batch_pk, "pk": line_pk}
        )

    def _get_payroll_lines_urL_by_batch(self, batch_pk):
        return reverse("payroll:payroll-line-list", kwargs={"batch_pk": batch_pk})

    def setUp(self):
        super().setUp()
        self.farm = Farm.objects.create(
            name="Test Farm",
            code="TSTF",
        )
        # Create a week payroll batch
        self.payroll_batch = PayrollBatch.objects.create(
            name="Test Payroll Batch", 
            start_date = date(2025, 6, 30),
            end_date = date(2025, 7, 6),
            farm=self.farm
        )
        # Seed field workers
        self.fw1 = FieldWorker.objects.create(
            name="John Doe",
            odoo_employee_id=1,
            odoo_contract_id=1,
            identification_number="1234567899",
            wage = 600.00,
            start_date = date(2025, 6, 30),
            contract_status="open",
        )
        self.fw2 = FieldWorker.objects.create(
            name="Jane Doe",
            odoo_employee_id=2,
            odoo_contract_id=2,
            identification_number="1234567898",
            wage = 480.00,
            start_date = date(2025, 6, 30),
            contract_status="open",
        )
        # Create some activities
        self.activity_group = ActivityGroup.objects.create(name="Test Activity Group", code="TSTAG")
        self.uom = Uom.objects.create(name="Units")
        self.work_labor_type = LaborType.objects.create(name="Test Work", code="TWT")
        self.leave_labor_type = LaborType.objects.create(
            name="Test Leave", 
            code="TLT",
            calculates_integral=False,
            calculates_thirteenth_bonus=False,
            calculates_fourteenth_bonus=False
        )
        self.work_activity1 = Activity.objects.create(
            name="Harvest",
            activity_group=self.activity_group,
            labor_type=self.work_labor_type,
            uom=self.uom
        )
        self.work_activity2 = Activity.objects.create(
            name="Plant",
            activity_group=self.activity_group,
            labor_type=self.work_labor_type,
            uom=self.uom
        )
        self.leave_activity = Activity.objects.create(
            name="Absence",
            activity_group=self.activity_group,
            labor_type=self.leave_labor_type,
            uom=self.uom
        )
        # Create some tariffs
        self.tariff1 = Tariff.objects.create(
            name="Test Tariff 1",
            activity=self.work_activity1,
            farm=self.farm,
            cost_per_unit=2.00
        )
        self.tariff2 = Tariff.objects.create(
            name="Test Tariff 2",
            activity=self.work_activity2,
            farm=self.farm,
            cost_per_unit=3.00
        )
        # Create some payroll batch lines
        self.fw1_line1 = PayrollBatchLine.objects.create(
            field_worker=self.fw1,
            payroll_batch=self.payroll_batch,
            activity=self.work_activity1,
            date = date(2025, 6, 30),
            quantity = 10,
        )
        self.fw1_line2 = PayrollBatchLine.objects.create(
            field_worker=self.fw1,
            payroll_batch=self.payroll_batch,
            activity=self.work_activity2,
            date = date(2025, 7, 1),
            quantity = 6,
        )
        # Create the system payroll config
        self.payroll_config = PayrollConfiguration.objects.create(
            id=1,
            mobilization_percentage=80,
            extra_hours_percentage=20,
            basic_monthly_wage=480,
            extra_hour_multiplier=1.5
        )
    
    def test_retrieve_batch_payroll_lines(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        
        self.assertEqual(res.data["results"][0]["field_worker"]["name"], "John Doe")
        self.assertEqual(res.data["results"][1]["field_worker"]["name"], "John Doe")
    
    def test_retrieve_specific_batch_payroll_line(self):
        url = self._get_payroll_line_detail_url_by_batch(self.payroll_batch.pk, self.fw1_line1.pk)

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["field_worker"]["name"], "John Doe")
    
    def test_filter_by_field_worker_identification(self):
        # Create a new line with a different field worker
        self.fw2_line = PayrollBatchLine.objects.create(
            field_worker=self.fw2,
            payroll_batch=self.payroll_batch,
            activity=self.work_activity1,
            date = date(2025, 6, 30),
            quantity = 10,
        )
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk) + "?field_worker__id=1234567899"

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        
        self.assertEqual(res.data["results"][0]["field_worker"]["name"], "John Doe")
        self.assertEqual(res.data["results"][1]["field_worker"]["name"], "John Doe")
    
    def test_filter_lines_by_field_worker_name(self):
        self.fw2_line = PayrollBatchLine.objects.create(
            field_worker=self.fw2,
            payroll_batch=self.payroll_batch,
            activity=self.work_activity1,
            date = date(2025, 6, 30),
            quantity = 10,
        )
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk) + "?field_worker__name=Jane Doe"

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        
        self.assertEqual(res.data["results"][0]["field_worker"]["name"], "Jane Doe")
    
    def test_filter_lines_by_date_range(self):
        self.fw2_line = PayrollBatchLine.objects.create(
            field_worker=self.fw2,
            payroll_batch=self.payroll_batch,
            activity=self.work_activity1,
            date = date(2025, 7, 10),
            quantity = 10,
        )
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk) + "?date__lte=2025-07-01"

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        
        self.assertEqual(res.data["results"][0]["field_worker"]["name"], "John Doe")
        self.assertEqual(res.data["results"][1]["field_worker"]["name"], "John Doe")

    def test_filter_lines_by_specific_date(self):
        self.fw2_line = PayrollBatchLine.objects.create(
            field_worker=self.fw2,
            payroll_batch=self.payroll_batch,
            activity=self.work_activity1,
            date = date(2025, 7, 1),
            quantity = 10,
        )
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk) + "?date=2025-07-01"

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        
        self.assertEqual(res.data["results"][0]["field_worker"]["name"], "John Doe")
        self.assertEqual(res.data["results"][1]["field_worker"]["name"], "Jane Doe")
    
    def test_create_batch_payroll_line(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertTrue(PayrollBatchLine.objects.filter(field_worker=self.fw2).exists())
        self.assertEqual(res.data["field_worker"], self.fw2.pk)
    
    def test_total_cost_is_calculated_on_creation(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Decimal(res.data["total_cost"]), Decimal('20.00'))
    
    def test_payroll_line_is_saved_with_iso_week_and_year(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(res.data["iso_week"], 27)
        self.assertEqual(res.data["iso_year"], 2025)
    
    def test_surplus_is_calculated_on_creation(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Decimal(res.data["salary_surplus"]), Decimal('4.00'))
    
    def test_mobilization_bonus_is_calculated_on_creation(self):
        """
        Test that the correct amount of mobilization bonus is calculated
        based on the salary surplus and the payroll configuration
        """
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Decimal(res.data["mobilization_bonus"]), Decimal('3.20'))
    
    def test_extra_hours_are_calculated_on_creation(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Decimal(res.data["extra_hours_value"]), Decimal('0.80'))
        self.assertEqual(Decimal(res.data["extra_hours_qty"]), Decimal('0.267'))
    
    def test_thirteenth_bonus_is_calculated_on_creation(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        # Calculate the daily thirteenth bonus and compared it
        fw_wage = self.fw2.wage or 0
        daily_thirteenth_bonus = (fw_wage / MONTHS_IN_YEAR) / DAYS_OF_THE_MONTH 

        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            Decimal(res.data["thirteenth_bonus"]), 
            Decimal(daily_thirteenth_bonus).quantize(Decimal('0.001'))
        )
    
    def test_fourteenth_bonus_is_calculated_on_creation(self):
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        # Calculate the daily fourteenth bonus and compared it
        basic_wage = self.payroll_config.basic_monthly_wage or 0
        daily_fourteenth_bonus = (basic_wage / MONTHS_IN_YEAR) / DAYS_OF_THE_MONTH 

        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(
            Decimal(res.data["fourteenth_bonus"]), 
            Decimal(daily_fourteenth_bonus).quantize(Decimal('0.001'))
        )
    
    def test_correct_integral_bonus_calculation(self):
        """
        Adding a new payroll line should trigger correct recalculation of integral bonus
        based on related workers records in the same week:
        - If a worker worked 5+ days, then he get 2 extra days salarys as integral bonus
        - If a worker worked 4 days, then he get 1 extra day salary as integral bonus
        - If a worker worked 3- days, then he get 0 extra day salary as integral bonus
        """
        fw1_daily_wage = (self.fw1.wage or 0) / DAYS_OF_THE_MONTH
        # Lets create a third line for fw1 for testing
        PayrollBatchLine.objects.create(
            field_worker=self.fw1, 
            payroll_batch=self.payroll_batch, 
            activity=self.work_activity1, 
            date = date(2025, 7, 2), 
            quantity = 10, 
        )
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        # Lets create a line for fw2, because its his first line, he should get 0 extra days
        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 1),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Decimal(res.data["integral_bonus"]), Decimal('0.00'))

        # Lets create another line for fw1, because this its his 4th line
        # he should get 1 extra day as integral bonus
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 3),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Decimal(res.data["integral_bonus"]), Decimal(fw1_daily_wage / 4))

        # Lets create another line for fw1, because this its his 5th line
        # he should get 2 extra days as integral bonus
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 4),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Decimal(res.data["integral_bonus"]), Decimal((fw1_daily_wage * 2) / 5))

        # Lets check that the other payroll lines related to the fw1
        # for this week should distribute evenly the integral bonus
        res = self.client.get(url + f"?field_worker__name={self.fw1.name}")
        for line in res.data["results"]:
            self.assertEqual(Decimal(line["integral_bonus"]), Decimal((fw1_daily_wage * 2) / 5))
    
    def test_calcs_distributed_proportionally_for_same_day_records(self):
        """
        Test that if a worker has more than one record in the same day,
        the all output calculations should be distributed proportionally
        based on the total activity cost
        """
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 2),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Create a second record for the same day
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 2),
            "activity": self.work_activity2.pk,
            "quantity": 4,
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # We need to assert that the output fields are distributed proportionally
        # for each record in the same day
        res = self.client.get(url + f"?field_worker__name={self.fw1.name}&date={date(2025, 7, 2)}")
        self.assertEqual(len(res.data["results"]), 2)

        # Compare the total cost
        self.assertEqual(Decimal(res.data["results"][0]["total_cost"]), Decimal('20.00'))
        self.assertEqual(Decimal(res.data["results"][1]["total_cost"]), Decimal('12.00'))

        # Salary surplus distirbution
        self.assertEqual(Decimal(res.data["results"][0]["salary_surplus"]), Decimal('7.50'))
        self.assertEqual(Decimal(res.data["results"][1]["salary_surplus"]), Decimal('4.50'))

        # Mobilization bonus distribution
        self.assertEqual(Decimal(res.data["results"][0]["mobilization_bonus"]), Decimal('6.00'))
        self.assertEqual(Decimal(res.data["results"][1]["mobilization_bonus"]), Decimal('3.60'))

        # Extra hours distribution
        self.assertEqual(Decimal(res.data["results"][0]["extra_hours_value"]), Decimal('1.50'))
        self.assertEqual(Decimal(res.data["results"][1]["extra_hours_value"]), Decimal('0.90'))

        # Thirteenth bonus distribution
        self.assertEqual(
            Decimal(res.data["results"][0]["thirteenth_bonus"]), 
            Decimal('1.0416').quantize(Decimal('0.001'))
        )
        self.assertEqual(
            Decimal(res.data["results"][1]["thirteenth_bonus"]), 
            Decimal('0.625').quantize(Decimal('0.001'))
        )

        # Fourteenth bonus distribution
        self.assertEqual(
            Decimal(res.data["results"][0]["fourteenth_bonus"]), 
            Decimal('0.8333').quantize(Decimal('0.001'))
        )
        self.assertEqual(
            Decimal(res.data["results"][1]["fourteenth_bonus"]), 
            Decimal('0.5').quantize(Decimal('0.001'))
        )

        # Integral bonus distribution
        self.assertEqual(Decimal(res.data["results"][0]["integral_bonus"]), Decimal('0.00'))
        self.assertEqual(Decimal(res.data["results"][1]["integral_bonus"]), Decimal('0.00'))
    
    def test_daily_payroll_line_limit_per_worker(self):
        """
        Test that the daily payroll line limit is applied per worker
        """
        self.payroll_config.daily_payroll_line_worker_limit = 1
        self.payroll_config.save()
        # Get all available configs
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 2),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Add another line for the same worker
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 2),
            "activity": self.work_activity2.pk,
            "quantity": 10,
        }
        
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Daily limit", str(res.data['daily_limit']))
    
    def test_line_update_recalculates_values(self):
        """
        Test that after modifying a line, the line is recalculated
        """
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        # Createa line 
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 2),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        line_id = res.data["id"]
        line_detail_url = self._get_payroll_line_detail_url_by_batch(self.payroll_batch.pk, line_id)

        # Update line with new values
        payload = {
            'quantity': 20,
        }
        res = self.client.patch(line_detail_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Check that line was recaculated
        self.assertEqual(Decimal(res.data["quantity"]), Decimal('20.000'))
        self.assertEqual(Decimal(res.data["total_cost"]), Decimal('40.00'))
        self.assertEqual(Decimal(res.data["salary_surplus"]), Decimal('20.00'))
        self.assertEqual(Decimal(res.data["mobilization_bonus"]), Decimal('16.00'))
        self.assertEqual(Decimal(res.data["extra_hours_value"]), Decimal('4.00'))
        self.assertEqual(Decimal(res.data["thirteenth_bonus"]), Decimal('1.6666667').quantize(Decimal('0.001')))
        self.assertEqual(Decimal(res.data["fourteenth_bonus"]), Decimal('1.333333').quantize(Decimal('0.001')))
        self.assertEqual(Decimal(res.data["integral_bonus"]), Decimal('0.00'))
    
    def test_line_update_recalculates_same_day_distribution(self):
        """
        When updating a line if there are other lines on the same day, they should be recalculated
        to distribute the amount proportionally
        """
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)

        # Createa a line
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 2),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        self.client.post(url, payload, format='json')

        # Create a new line on same day, different activity
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 2),
            "activity": self.work_activity2.pk,
            "quantity": 1,
        }
        res = self.client.post(url, payload, format='json')
        line_id = res.data["id"]

        # Update line with new values
        payload = {
            'quantity': 5,
        }
        line_detail_url = self._get_payroll_line_detail_url_by_batch(self.payroll_batch.pk, line_id)
        res = self.client.patch(line_detail_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Check that each line for the same day was recaculated
        same_day_lines = PayrollBatchLine.objects.filter(date=date(2025, 7, 2))
        self.assertEqual(same_day_lines[0].salary_surplus, Decimal('8.571'))
        self.assertEqual(same_day_lines[1].salary_surplus, Decimal('6.429'))
        self.assertEqual(same_day_lines[0].mobilization_bonus, Decimal('6.857'))
        self.assertEqual(same_day_lines[1].mobilization_bonus, Decimal('5.143'))
        self.assertEqual(same_day_lines[0].extra_hours_value, Decimal('1.714'))
        self.assertEqual(same_day_lines[1].extra_hours_value, Decimal('1.286'))
    
    def test_line_update_recalculates_week_integral(self):
        """
        When a line is updated, the integral bonus should be recalculated
        """
        # Create four lines for a worker in a week
        PayrollBatchLine.objects.create(
            field_worker=self.fw1, 
            activity=self.work_activity1, 
            quantity=10, date=date(2025, 7, 2), 
            payroll_batch=self.payroll_batch
        )
        PayrollBatchLine.objects.create(
            field_worker=self.fw1, 
            activity=self.work_activity1, 
            quantity=10, date=date(2025, 7, 3), 
            payroll_batch=self.payroll_batch
        )
        # Add another line through the API to trigger recalculations
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 4),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format='json')
        line_id = res.data["id"]
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Check that all lines we updated with correct integral
        fw_lines = PayrollBatchLine.objects.filter(field_worker=self.fw1)
        for line in fw_lines:
            self.assertEqual(line.integral_bonus, Decimal('8.00'))
        
        # Update a line activity for something that does not cound as worked day
        url = self._get_payroll_line_detail_url_by_batch(self.payroll_batch.pk, line_id)
        payload = {
            "activity": self.leave_activity.pk,
        }
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(res.data["integral_bonus"]), Decimal('0.000'))

        # Check that all lines we updated with correct integral
        fw_lines = PayrollBatchLine.objects.filter(
            field_worker=self.fw1,
            integral_bonus__gt=0
        )
        for line in fw_lines:
            self.assertEqual(line.integral_bonus, Decimal('5.00'))
    
    def test_deleting_a_line(self):
        # Create a line for fw2
        payload = {
            "field_worker": self.fw2.pk,
            "date": date(2025, 7, 5),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        
        }
        res = self.client.post(self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk), payload, format='json')
        self.assertEqual(PayrollBatchLine.objects.filter(field_worker=self.fw2).count(), 1)

        line_id = res.data["id"]
        url = self._get_payroll_line_detail_url_by_batch(self.payroll_batch.pk, line_id)
        logger.info(f"Deleting line with id {line_id} wiht url {url}")
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PayrollBatchLine.objects.filter(field_worker=self.fw2).count(), 0)

    def test_deleting_line_recalculates_week_integral(self):
        """
        When a line is deleted, the integral bonus should be recalculated
        """
        # Create four lines for a worker in a week
        PayrollBatchLine.objects.create(
            field_worker=self.fw1, 
            activity=self.work_activity1, 
            quantity=10, date=date(2025, 7, 2), 
            payroll_batch=self.payroll_batch
        )
        PayrollBatchLine.objects.create(
            field_worker=self.fw1, 
            activity=self.work_activity1, 
            quantity=10, date=date(2025, 7, 3), 
            payroll_batch=self.payroll_batch
        )
        # Add another line through the API to trigger recalculations
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 4),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }

        res = self.client.post(url, payload, format='json')
        line_id = res.data["id"]
        
        # Delete a line
        url = self._get_payroll_line_detail_url_by_batch(self.payroll_batch.pk, line_id)
        res = self.client.delete(url)

        # Check that all lines we updated with correct integral
        fw_lines = PayrollBatchLine.objects.filter(field_worker=self.fw1)
        for line in fw_lines:
            self.assertEqual(line.integral_bonus, Decimal('5.00'))
        
    def test_deleting_line_recalculates_same_day_distribution(self):
        """
        When a line is deleted, if there were other lines on the same day, 
        the weekly bonuses should be recalculated
        """
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 15),
            "activity": self.work_activity1.pk,
            "quantity": 10,
        }
        url = self._get_payroll_lines_urL_by_batch(self.payroll_batch.pk)
        res = self.client.post(url , payload, format='json')

        # Create another line for the same day
        payload = {
            "field_worker": self.fw1.pk,
            "date": date(2025, 7, 15),
            "activity": self.work_activity2.pk,
            "quantity": 10,
        }
        res = self.client.post(url, payload, format='json')

        line_id = res.data["id"]

        # Delete a line
        url = self._get_payroll_line_detail_url_by_batch(self.payroll_batch.pk, line_id)
        res = self.client.delete(url)

        # Check that all lines we updated with correct integral
        fw_lines = PayrollBatchLine.objects.filter(field_worker=self.fw1, date=date(2025, 7, 15))
        self.assertEqual(fw_lines[0].salary_surplus, Decimal('0.00'))
        self.assertEqual(fw_lines[0].mobilization_bonus, Decimal('0.00'))
        self.assertEqual(fw_lines[0].extra_hours_value, Decimal('0.00'))
    