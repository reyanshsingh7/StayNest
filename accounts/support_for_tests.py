"""
Shared helpers for StayNest tests (deliberately not named test*.py).

* StayNestTestCase replaces all templates with tiny stand-ins, so the backend
  tests keep working even before the frontend developer's templates exist.
  Run the application in the browser to test the real templates.
* make_* helpers create users and properties quickly.

IMPORTANT: make_property() assumes the agreed model contract in
docs/DATABASE_CONTRACT.md. If the database developer's field names differ,
fix them here once.
"""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from accounts.models import User

TEMPLATE_NAMES = [
    "accounts/login.html",
    "accounts/register.html",
    "home.html",
    "bookings/student_dashboard.html",
    "bookings/owner_dashboard.html",
    "bookings/my_requests.html",
    "bookings/owner_requests.html",
    "properties/property_list.html",
    "properties/property_detail.html",
    "properties/property_form.html",
    "properties/my_properties.html",
    "partials/booking_card.html",
    "partials/dashboard_nav.html",
    "partials/field.html",
    "partials/owner_property_card.html",
    "partials/property_card.html",
    "partials/status_badge.html",
]

STUB_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.locmem.Loader",
                    {name: "stub page" for name in TEMPLATE_NAMES},
                )
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

PASSWORD = "Str0ng-Test-Pass!"


@override_settings(TEMPLATES=STUB_TEMPLATES)
class StayNestTestCase(TestCase):
    """Base class: stub templates + helpers."""

    def login_as(self, user):
        self.client.force_login(user)

    def message_texts(self, response):
        return [str(m) for m in response.context["messages"]] if response.context else []


def make_student(email="student@example.com", name="Test Student"):
    return User.objects.create_user(email=email, password=PASSWORD, full_name=name, role=User.Role.STUDENT)


def make_owner(email="owner@example.com", name="Test Owner"):
    return User.objects.create_user(email=email, password=PASSWORD, full_name=name, role=User.Role.OWNER)


def make_property(owner, **overrides):
    from properties.models import Property

    data = {
        "owner": owner,
        "name": "Sunrise PG",
        "property_type": "pg",
        "description": "A clean and friendly PG close to the university campus.",
        "city": "Delhi",
        "locality": "Mukherjee Nagar",
        "address": "12 Main Road, Mukherjee Nagar",
        "postal_code": "110009",
        "monthly_rent": 6000,
        "approval_status": "approved",
        "is_available": True,
    }
    data.update(overrides)
    return Property.objects.create(**data)


def valid_property_data(**overrides):
    """POST data for PropertyForm (amenities left out = unchecked)."""
    data = {
        "name": "Green Valley Hostel",
        "property_type": "hostel",
        "accommodation_for": "all",
        "description": "Spacious rooms, good food and a quiet study area.",
        "city": "Noida",
        "locality": "Sector 62",
        "address": "Plot 5, Sector 62, Noida",
        "postal_code": "201301",
        "monthly_rent": "7500",
        "is_available": "on",
    }
    data.update(overrides)
    return data


def make_image_file(name="photo.png", fmt="PNG", content_type="image/png"):
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), "teal").save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class TemporaryMediaMixin:
    """Send uploaded files to a temporary folder and delete it afterwards."""

    @classmethod
    def setUpClass(cls):
        cls._media_dir = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)
