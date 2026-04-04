from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import (
    Hospital, HospitalStatus, PatientEvent,
    TransferRequest, Notification, AuditLog
)
from .forms import TriageForm, HospitalStatusForm, SOSForm

User = get_user_model()

# PART 1 — Hospital & HospitalStatus Model Tests

class HospitalModelTest(TestCase):

    def setUp(self):
        self.hospital = Hospital.objects.create(
            name='Dhaka Medical College',
            address='Bakshibazar, Dhaka',
            latitude=23.7243,
            longitude=90.3946,
            phone_number='01700000001',
            specialty='general',
        )

    def test_hospital_created_successfully(self):
        self.assertEqual(self.hospital.name, 'Dhaka Medical College')
        self.assertEqual(self.hospital.specialty, 'general')

    def test_hospital_is_active_by_default(self):
        self.assertTrue(self.hospital.is_active)

    def test_hospital_str(self):
        self.assertEqual(str(self.hospital), 'Dhaka Medical College')

    def test_hospital_specialty_cardiac(self):
        h = Hospital.objects.create(
            name='Heart Hospital', address='Dhaka',
            latitude=23.7, longitude=90.4,
            phone_number='01700000002', specialty='cardiac',
        )
        self.assertEqual(h.specialty, 'cardiac')

    def test_inactive_hospital_not_in_active_filter(self):
        self.hospital.is_active = False
        self.hospital.save()
        self.assertNotIn(self.hospital, Hospital.objects.filter(is_active=True))

    def test_multiple_hospitals_count(self):
        Hospital.objects.create(
            name='Square Hospital', address='Panthapath',
            latitude=23.75, longitude=90.38,
            phone_number='01700000003',
        )
        self.assertEqual(Hospital.objects.count(), 2)


class HospitalStatusModelTest(TestCase):

    def setUp(self):
        self.hospital = Hospital.objects.create(
            name='Square Hospital', address='Dhaka',
            latitude=23.75, longitude=90.38,
            phone_number='01711111111',
        )
        self.admin_user = User.objects.create_user(
            username='hospital_admin1', password='AdminPass123!',
            role='hospital_admin',
        )
        self.status = HospitalStatus.objects.create(
            hospital=self.hospital,
            updated_by=self.admin_user,
            icu_total=20, icu_available=5,
            bed_total=100, bed_available=30,
            has_ventilator=True,
            has_blood_bank=False,
            is_accepting=True,
        )

    def test_status_created(self):
        self.assertEqual(self.status.hospital.name, 'Square Hospital')
        self.assertTrue(self.status.is_accepting)

    def test_icu_load_percent(self):
        # (20-5)/20 * 100 = 75%
        self.assertEqual(self.status.icu_load_percent, 75)

    def test_bed_load_percent(self):
        # (100-30)/100 * 100 = 70%
        self.assertEqual(self.status.bed_load_percent, 70)

    def test_icu_load_when_total_zero_returns_100(self):
        self.status.icu_total = 0
        self.assertEqual(self.status.icu_load_percent, 100)

    def test_bed_load_when_total_zero_returns_100(self):
        self.status.bed_total = 0
        self.assertEqual(self.status.bed_load_percent, 100)

    def test_full_icu_capacity(self):
        self.status.icu_available = 0
        self.assertEqual(self.status.icu_load_percent, 100)

    def test_status_str_contains_hospital_name(self):
        self.assertIn('Square Hospital', str(self.status))

    def test_has_ventilator_true_blood_bank_false(self):
        self.assertTrue(self.status.has_ventilator)
        self.assertFalse(self.status.has_blood_bank)


class HospitalAdminAssignmentTest(TestCase):

    def setUp(self):
        self.hospital = Hospital.objects.create(
            name='Lab Aid Hospital', address='Dhanmondi',
            latitude=23.74, longitude=90.37,
            phone_number='01722222222',
        )
        self.admin_user = User.objects.create_user(
            username='lab_admin', password='AdminPass123!',
            role='hospital_admin',
            hospital=self.hospital,
        )

    def test_user_has_hospital_assigned(self):
        self.assertEqual(self.admin_user.hospital, self.hospital)

    def test_is_hospital_admin_property(self):
        self.assertTrue(self.admin_user.is_hospital_admin)

    def test_user_without_hospital_is_none(self):
        user = User.objects.create_user(
            username='no_hosp_admin', password='Pass1234!',
            role='hospital_admin',
        )
        self.assertIsNone(user.hospital)

    def test_multiple_admins_for_one_hospital(self):
        User.objects.create_user(
            username='admin2', password='Pass1234!',
            role='hospital_admin', hospital=self.hospital,
        )
        self.assertEqual(User.objects.filter(hospital=self.hospital).count(), 2)


