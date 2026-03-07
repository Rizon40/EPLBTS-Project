from django.test import TestCase
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from .models import Hospital, HospitalStatus, PatientEvent, TransferRequest, Notification, AuditLog

User = get_user_model()


class HospitalTest(TestCase):

    def test_create_hospital(self):
        h = Hospital.objects.create(
            name='Dhaka Medical', address='Dhaka',
            latitude=23.72, longitude=90.39, phone_number='000',
        )
        self.assertEqual(str(h), 'Dhaka Medical')
        self.assertTrue(h.is_active)
        self.assertEqual(h.specialty, 'general')


class HospitalStatusTest(TestCase):

    def setUp(self):
        self.hospital = Hospital.objects.create(
            name='Square', address='Dhaka', latitude=23.75, longitude=90.39, phone_number='0',
        )
        self.status = HospitalStatus.objects.create(
            hospital=self.hospital, icu_total=20, icu_available=5,
            bed_total=100, bed_available=30,
        )

    def test_icu_load_percent(self):
        self.assertEqual(self.status.icu_load_percent, 75)

    def test_bed_load_percent(self):
        self.assertEqual(self.status.bed_load_percent, 70)

    def test_zero_total_returns_100(self):
        self.status.icu_total = 0
        self.assertEqual(self.status.icu_load_percent, 100)


class PatientEventTest(TestCase):

    def test_create_event(self):
        user = User.objects.create_user(username='p1', password='Pass1234!')
        event = PatientEvent.objects.create(
            submitted_by=user, case_type='accident',
            patient_age=35, patient_gender='male', location_text='Mirpur',
        )
        self.assertEqual(event.status, 'pending')
        self.assertIn('Road Accident', str(event))


class TransferRequestTest(TestCase):

    def test_create_and_one_to_one(self):
        user = User.objects.create_user(username='p1', password='Pass1234!')
        hospital = Hospital.objects.create(
            name='NHF', address='Dhaka', latitude=23.8, longitude=90.3, phone_number='0',
        )
        event = PatientEvent.objects.create(
            submitted_by=user, case_type='heart_attack',
            patient_age=55, patient_gender='male', location_text='Dhanmondi',
        )
        transfer = TransferRequest.objects.create(
            patient_event=event, hospital=hospital, requested_by=user,
        )
        self.assertEqual(transfer.status, 'pending')
        self.assertFalse(transfer.is_overridden)

        # same event e duplicate transfer hobe na
        with self.assertRaises(IntegrityError):
            TransferRequest.objects.create(
                patient_event=event, hospital=hospital, requested_by=user,
            )


class NotificationTest(TestCase):

    def test_create_notification(self):
        user = User.objects.create_user(username='a1', password='Pass1234!')
        hospital = Hospital.objects.create(
            name='Lab Aid', address='Dhaka', latitude=23.75, longitude=90.39, phone_number='0',
        )
        event = PatientEvent.objects.create(
            submitted_by=user, case_type='burn',
            patient_age=25, patient_gender='female', location_text='Mohammadpur',
        )
        transfer = TransferRequest.objects.create(
            patient_event=event, hospital=hospital, requested_by=user,
        )
        notif = Notification.objects.create(
            hospital=hospital, transfer_request=transfer, message='Burn patient incoming',
        )
        self.assertEqual(notif.status, 'pending')
        self.assertIn('Lab Aid', str(notif))


class AuditLogTest(TestCase):

    def test_create_log(self):
        user = User.objects.create_user(username='a1', password='Pass1234!')
        log = AuditLog.objects.create(
            performed_by=user, action='triage_submitted', description='New triage case',
        )
        self.assertIn('Triage Submitted', str(log))
        self.assertIsNone(log.patient_event)
