"""
Test-support helpers shared by properties/test_models.py and bookings/test_models.py.

make_user() adapts to the project lead's custom user model: it uses USERNAME_FIELD
(email by default) and sets ``role`` only if the user model has such a field.
If the real user model needs other required fields, edit make_user() here.
"""
import io
from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from .models import Property

_counter = count(1)


def _role_value(user_model, wanted):
    """Map 'owner'/'student' onto the user model's actual role choice values."""
    field = user_model._meta.get_field("role")
    for value, label in field.choices or []:
        if str(value).lower() == wanted or str(label).lower() == wanted:
            return value
    return wanted


def make_user(role="student", email=None, password="StrongPass123!"):
    User = get_user_model()
    identifier = email or f"{role}{next(_counter)}@example.com"
    field_names = {f.name for f in User._meta.get_fields()}
    kwargs = {User.USERNAME_FIELD: identifier}
    if User.USERNAME_FIELD != "email" and "email" in field_names:
        kwargs["email"] = identifier
    if "role" in field_names:
        kwargs["role"] = _role_value(User, role)
    return User.objects.create_user(password=password, **kwargs)


def make_property(owner=None, **overrides):
    data = {
        "owner": owner or make_user("owner"),
        "name": "Sunrise PG",
        "property_type": Property.PropertyType.PG,
        "description": "Clean rooms close to the college campus.",
        "city": "Greater Noida",
        "locality": "Knowledge Park III",
        "address": "Plot 12, Knowledge Park III",
        "postal_code": "201310",
        "monthly_rent": Decimal("7500.00"),
    }
    data.update(overrides)
    return Property.objects.create(**data)


def make_bookable_property(owner=None, **overrides):
    """Approved + available property: the only kind that accepts booking requests."""
    overrides.setdefault("approval_status", Property.ApprovalStatus.APPROVED)
    return make_property(owner=owner, **overrides)


def make_image_file(name="photo.png", size=(10, 10), image_format="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(200, 80, 80)).save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")
