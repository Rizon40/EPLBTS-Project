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

# PART 2 — Hospital Status View & Form Tests
class HospitalStatusFormTest(TestCase):

    def test_valid_form(self):
        data = {
            'icu_total': 20, 'icu_available': 10,
            'bed_total': 100, 'bed_available': 50,
            'has_ventilator': True, 'has_blood_bank': False,
            'has_cath_lab': False, 'is_accepting': True,
        }
        self.assertTrue(HospitalStatusForm(data=data).is_valid())

    def test_missing_icu_total_invalid(self):
        data = {
            'icu_total': '', 'icu_available': 10,
            'bed_total': 100, 'bed_available': 50,
            'is_accepting': True,
        }
        self.assertFalse(HospitalStatusForm(data=data).is_valid())

    def test_negative_value_invalid(self):
        data = {
            'icu_total': -5, 'icu_available': 10,
            'bed_total': 100, 'bed_available': 50,
            'is_accepting': True,
        }
        self.assertFalse(HospitalStatusForm(data=data).is_valid())

    def test_all_checkboxes_false_valid(self):
        data = {
            'icu_total': 10, 'icu_available': 5,
            'bed_total': 50, 'bed_available': 20,
            'has_ventilator': False, 'has_blood_bank': False,
            'has_cath_lab': False, 'is_accepting': False,
        }
        self.assertTrue(HospitalStatusForm(data=data).is_valid())


class UpdateHospitalStatusViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.hospital = Hospital.objects.create(
            name='Green Life Hospital', address='Dhaka',
            latitude=23.76, longitude=90.39,
            phone_number='01733333333',
        )
        self.admin_user = User.objects.create_user(
            username='green_admin', password='AdminPass123!',
            role='hospital_admin', hospital=self.hospital,
        )
        self.paramedic = User.objects.create_user(
            username='paramedic1', password='Pass1234!',
            role='paramedic',
        )

    def get_status_data(self):
        return {
            'icu_total': 15, 'icu_available': 7,
            'bed_total': 80, 'bed_available': 40,
            'has_ventilator': True, 'has_blood_bank': True,
            'has_cath_lab': False, 'is_accepting': True,
        }

    def test_login_required(self):
        resp = self.client.get(reverse('update_hospital_status'))
        self.assertEqual(resp.status_code, 302)

    def test_paramedic_cannot_access(self):
        self.client.login(username='paramedic1', password='Pass1234!')
        resp = self.client.get(reverse('update_hospital_status'))
        self.assertRedirects(resp, reverse('dashboard'))

    def test_hospital_admin_can_access(self):
        self.client.login(username='green_admin', password='AdminPass123!')
        resp = self.client.get(reverse('update_hospital_status'))
        self.assertEqual(resp.status_code, 200)

    def test_valid_post_creates_status(self):
        self.client.login(username='green_admin', password='AdminPass123!')
        self.client.post(reverse('update_hospital_status'), self.get_status_data())
        self.assertTrue(HospitalStatus.objects.filter(hospital=self.hospital).exists())

    def test_status_saved_with_correct_hospital_and_user(self):
        self.client.login(username='green_admin', password='AdminPass123!')
        self.client.post(reverse('update_hospital_status'), self.get_status_data())
        status = HospitalStatus.objects.filter(hospital=self.hospital).first()
        self.assertEqual(status.hospital, self.hospital)
        self.assertEqual(status.updated_by, self.admin_user)

    def test_admin_without_hospital_redirects(self):
        no_hosp = User.objects.create_user(
            username='no_hosp', password='Pass1234!',
            role='hospital_admin',
        )
        self.client.login(username='no_hosp', password='Pass1234!')
        resp = self.client.get(reverse('update_hospital_status'))
        self.assertRedirects(resp, reverse('dashboard'))

    def test_status_update_creates_audit_log(self):
        self.client.login(username='green_admin', password='AdminPass123!')
        self.client.post(reverse('update_hospital_status'), self.get_status_data())
        self.assertTrue(AuditLog.objects.filter(action='status_updated').exists())


class HospitalListViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='any_user', password='Pass1234!',
            role='paramedic',
        )
        Hospital.objects.create(
            name='Enam Medical', address='Savar',
            latitude=23.85, longitude=90.26,
            phone_number='01744444444', is_active=True,
        )
        Hospital.objects.create(
            name='Old Hospital', address='Dhaka',
            latitude=23.70, longitude=90.40,
            phone_number='01755555555', is_active=False,
        )

    def test_login_required(self):
        resp = self.client.get(reverse('hospital_list'))
        self.assertEqual(resp.status_code, 302)

    def test_logged_in_user_can_see_list(self):
        self.client.login(username='any_user', password='Pass1234!')
        resp = self.client.get(reverse('hospital_list'))
        self.assertEqual(resp.status_code, 200)

    def test_only_active_hospitals_shown(self):
        self.client.login(username='any_user', password='Pass1234!')
        resp = self.client.get(reverse('hospital_list'))
        self.assertEqual(resp.context['hospitals'].count(), 1)

    def test_hospitals_key_in_context(self):
        self.client.login(username='any_user', password='Pass1234!')
        resp = self.client.get(reverse('hospital_list'))
        self.assertIn('hospitals', resp.context)


# PART 3 — Triage & SOS Tests
class TriageFormTest(TestCase):

    def get_valid_data(self):
        return {
            'case_type': 'accident',
            'description': 'Car accident on highway',
            'patient_age': 30,
            'patient_gender': 'male',
            'location_text': 'Mirpur 10, Dhaka',
            'latitude': 23.80,
            'longitude': 90.36,
            'needs_icu': False,
            'needs_ventilator': False,
            'needs_blood_bank': True,
            'needs_cath_lab': False,
        }

    def test_valid_form(self):
        self.assertTrue(TriageForm(data=self.get_valid_data()).is_valid())

    def test_missing_case_type_invalid(self):
        data = self.get_valid_data()
        data['case_type'] = ''
        self.assertFalse(TriageForm(data=data).is_valid())

    def test_missing_location_invalid(self):
        data = self.get_valid_data()
        data['location_text'] = ''
        self.assertFalse(TriageForm(data=data).is_valid())

    def test_missing_patient_age_invalid(self):
        data = self.get_valid_data()
        data['patient_age'] = ''
        self.assertFalse(TriageForm(data=data).is_valid())

    def test_latitude_longitude_optional(self):
        data = self.get_valid_data()
        data['latitude'] = ''
        data['longitude'] = ''
        self.assertTrue(TriageForm(data=data).is_valid())

    def test_all_needs_checked_valid(self):
        data = self.get_valid_data()
        data.update({
            'needs_icu': True, 'needs_ventilator': True,
            'needs_blood_bank': True, 'needs_cath_lab': True,
        })
        self.assertTrue(TriageForm(data=data).is_valid())


class SubmitTriageViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.paramedic = User.objects.create_user(
            username='para1', password='Pass1234!',
            role='paramedic',
        )
        self.hospital_admin = User.objects.create_user(
            username='hadmin1', password='Pass1234!',
            role='hospital_admin',
        )

    def get_triage_data(self):
        return {
            'case_type': 'stroke',
            'description': 'Sudden stroke at home',
            'patient_age': 55,
            'patient_gender': 'female',
            'location_text': 'Dhanmondi, Dhaka',
            'needs_icu': True,
            'needs_ventilator': False,
            'needs_blood_bank': False,
            'needs_cath_lab': False,
        }

    def test_login_required(self):
        resp = self.client.get(reverse('submit_triage'))
        self.assertEqual(resp.status_code, 302)

    def test_hospital_admin_cannot_submit_triage(self):
        self.client.login(username='hadmin1', password='Pass1234!')
        resp = self.client.get(reverse('submit_triage'))
        self.assertRedirects(resp, reverse('dashboard'))

    def test_paramedic_can_access_triage_form(self):
        self.client.login(username='para1', password='Pass1234!')
        resp = self.client.get(reverse('submit_triage'))
        self.assertEqual(resp.status_code, 200)

    def test_triage_submitted_creates_event(self):
        self.client.login(username='para1', password='Pass1234!')
        self.client.post(reverse('submit_triage'), self.get_triage_data())
        self.assertEqual(PatientEvent.objects.count(), 1)

    def test_triage_submitted_by_correct_user(self):
        self.client.login(username='para1', password='Pass1234!')
        self.client.post(reverse('submit_triage'), self.get_triage_data())
        self.assertEqual(PatientEvent.objects.first().submitted_by, self.paramedic)

    def test_triage_default_status_pending(self):
        self.client.login(username='para1', password='Pass1234!')
        self.client.post(reverse('submit_triage'), self.get_triage_data())
        self.assertEqual(PatientEvent.objects.first().status, 'pending')

    def test_triage_redirects_to_success_page(self):
        self.client.login(username='para1', password='Pass1234!')
        resp = self.client.post(reverse('submit_triage'), self.get_triage_data())
        event = PatientEvent.objects.first()
        self.assertRedirects(resp, reverse('triage_success', kwargs={'pk': event.pk}))

    def test_triage_creates_audit_log(self):
        self.client.login(username='para1', password='Pass1234!')
        self.client.post(reverse('submit_triage'), self.get_triage_data())
        self.assertTrue(AuditLog.objects.filter(action='triage_submitted').exists())


class SOSEmergencyViewTest(TestCase):

    def setUp(self):
        self.client = Client()

    def get_sos_data(self):
        return {
            'case_type': 'heart_attack',
            'description': 'Chest pain, unconscious',
            'patient_age': 60,
            'patient_gender': 'male',
            'location_text': 'Gulshan, Dhaka',
            'phone_number': '01799999999',
        }

    def test_sos_page_accessible_without_login(self):
        resp = self.client.get(reverse('sos_emergency'))
        self.assertEqual(resp.status_code, 200)

    def test_sos_submit_without_login(self):
        self.client.post(reverse('sos_emergency'), self.get_sos_data())
        self.assertEqual(PatientEvent.objects.count(), 1)

    def test_sos_phone_number_saved(self):
        self.client.post(reverse('sos_emergency'), self.get_sos_data())
        self.assertEqual(PatientEvent.objects.first().phone_number, '01799999999')

    def test_sos_status_is_pending(self):
        self.client.post(reverse('sos_emergency'), self.get_sos_data())
        self.assertEqual(PatientEvent.objects.first().status, 'pending')

    def test_sos_missing_phone_does_not_save(self):
        data = self.get_sos_data()
        data['phone_number'] = ''
        self.client.post(reverse('sos_emergency'), data)
        self.assertEqual(PatientEvent.objects.count(), 0)

    def test_sos_redirects_to_success(self):
        resp = self.client.post(reverse('sos_emergency'), self.get_sos_data())
        event = PatientEvent.objects.first()
        self.assertRedirects(resp, reverse('sos_success', kwargs={'pk': event.pk}))

    def test_sos_creates_audit_log(self):
        self.client.post(reverse('sos_emergency'), self.get_sos_data())
        self.assertTrue(AuditLog.objects.filter(action='triage_submitted').exists())
