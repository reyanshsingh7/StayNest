from django.urls import reverse

from .models import User
from .support_for_tests import PASSWORD, StayNestTestCase, make_owner, make_student


class RegistrationTests(StayNestTestCase):
    def post_register(self, **overrides):
        data = {
            "full_name": "Asha Verma",
            "email": "asha@example.com",
            "role": "STUDENT",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("register"), data)

    def test_student_registration_assigns_student_role(self):
        response = self.post_register()
        self.assertRedirects(response, reverse("student_dashboard"))
        user = User.objects.get(email="asha@example.com")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.check_password(PASSWORD))

    def test_owner_registration_assigns_owner_role(self):
        response = self.post_register(email="owner1@example.com", role="OWNER")
        self.assertRedirects(response, reverse("owner_dashboard"))
        self.assertEqual(User.objects.get(email="owner1@example.com").role, User.Role.OWNER)

    def test_cannot_register_as_admin_role(self):
        response = self.post_register(role="ADMIN")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="asha@example.com").exists())

    def test_cannot_make_yourself_staff_or_superuser(self):
        self.post_register(is_staff="on", is_superuser="on")
        user = User.objects.get(email="asha@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        make_student(email="asha@example.com")
        response = self.post_register(email="ASHA@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="asha@example.com").count(), 1)

    def test_password_mismatch_is_rejected(self):
        response = self.post_register(password2="different-Pass-123")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="asha@example.com").exists())

    def test_weak_password_is_rejected(self):
        response = self.post_register(password1="12345678", password2="12345678")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="asha@example.com").exists())


class LoginLogoutTests(StayNestTestCase):
    def test_login_with_email_redirects_student_to_dashboard(self):
        make_student(email="s@example.com")
        response = self.client.post(reverse("login"), {"username": "S@Example.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("student_dashboard"))

    def test_login_redirects_owner_to_owner_dashboard(self):
        make_owner(email="o@example.com")
        response = self.client.post(reverse("login"), {"username": "o@example.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("owner_dashboard"))

    def test_wrong_password_fails(self):
        make_student(email="s@example.com")
        response = self.client.post(reverse("login"), {"username": "s@example.com", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unsafe_next_url_is_ignored(self):
        make_student(email="s@example.com")
        url = reverse("login") + "?next=https://evil.example.com/"
        response = self.client.post(url, {"username": "s@example.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("student_dashboard"))

    def test_logout_requires_post(self):
        user = make_student()
        self.login_as(user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_post_logs_out(self):
        self.login_as(make_student())
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)


class UserManagerTests(StayNestTestCase):
    def test_create_superuser_sets_admin_flags(self):
        admin = User.objects.create_superuser(email="Admin@Example.com", password=PASSWORD, full_name="Admin")
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.assertEqual(admin.email, "admin@example.com")

    def test_create_user_is_not_staff(self):
        user = User.objects.create_user(email="x@example.com", password=PASSWORD, full_name="X")
        self.assertFalse(user.is_staff or user.is_superuser)

    def test_create_user_without_email_fails(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password=PASSWORD, full_name="X")


class DashboardAccessTests(StayNestTestCase):
    def test_anonymous_is_sent_to_login_with_next(self):
        url = reverse("student_dashboard")
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def test_student_cannot_open_owner_dashboard(self):
        self.login_as(make_student())
        response = self.client.get(reverse("owner_dashboard"))
        self.assertRedirects(response, reverse("student_dashboard"), fetch_redirect_response=False)

    def test_owner_cannot_open_student_dashboard(self):
        self.login_as(make_owner())
        response = self.client.get(reverse("student_dashboard"))
        self.assertRedirects(response, reverse("owner_dashboard"), fetch_redirect_response=False)

    def test_student_dashboard_context_for_new_student(self):
        self.login_as(make_student())
        response = self.client.get(reverse("student_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 0)
        self.assertEqual(response.context["pending_count"], 0)

    def test_owner_dashboard_context_for_new_owner(self):
        self.login_as(make_owner())
        response = self.client.get(reverse("owner_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["property_count"], 0)
        self.assertEqual(response.context["pending_requests_count"], 0)
