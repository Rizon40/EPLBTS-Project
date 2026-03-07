from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .forms import RegisterForm, LoginForm

User = get_user_model()


# ------------------------Model Test ---------------------
class CustomUserModelTest(TestCase):

    def test_create_user_with_role(self):
        user = User.objects.create_user(
            username='testuser', password='TestPass123!',
            email='test@example.com', role='paramedic',
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, 'paramedic')
        self.assertTrue(user.check_password('TestPass123!'))

    def test_default_role(self):
        user = User.objects.create_user(username='u2', password='Pass1234!')
        self.assertEqual(user.role, 'paramedic')

    def test_str(self):
        user = User.objects.create_user(username='u3', password='Pass1234!', role='paramedic')
        self.assertEqual(str(user), 'u3 (Paramedic / Ambulance Operator)')

    def test_role_properties(self):
        user = User.objects.create_user(username='u4', password='Pass1234!', role='hospital_admin')
        self.assertTrue(user.is_hospital_admin)
        self.assertFalse(user.is_paramedic)


# ----------------------Form Tests-----------------
class RegisterFormTest(TestCase):

    def test_valid(self):
        data = {
            'username': 'new', 'email': 'n@e.com', 'role': 'paramedic',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        }
        self.assertTrue(RegisterForm(data=data).is_valid())

    def test_password_mismatch(self):
        data = {
            'username': 'new', 'email': 'n@e.com', 'role': 'paramedic',
            'password1': 'StrongPass123!', 'password2': 'Wrong456!',
        }
        self.assertFalse(RegisterForm(data=data).is_valid())

    def test_missing_email(self):
        data = {
            'username': 'new', 'email': '', 'role': 'paramedic',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        }
        self.assertFalse(RegisterForm(data=data).is_valid())


class LoginFormTest(TestCase):

    def test_valid(self):
        self.assertTrue(LoginForm(data={'username': 'u', 'password': 'p'}).is_valid())

    def test_empty_invalid(self):
        self.assertFalse(LoginForm(data={'username': '', 'password': ''}).is_valid())


# ---------------View Tests ------------------
class ViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='TestPass123!')

    def test_register_get(self):
        resp = self.client.get(reverse('register'))
        self.assertEqual(resp.status_code, 200)

    def test_register_post_valid(self):
        data = {
            'username': 'newuser', 'email': 'n@e.com', 'role': 'paramedic',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        }
        resp = self.client.post(reverse('register'), data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_valid(self):
        resp = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'TestPass123!'})
        self.assertRedirects(resp, reverse('dashboard'))

    def test_login_invalid(self):
        resp = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrong'})
        self.assertEqual(resp.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser', password='TestPass123!')
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, reverse('login'))

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_after_login(self):
        self.client.login(username='testuser', password='TestPass123!')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
