"""
StayNest - property models.

Models in this module
---------------------
Amenity        Predefined checklist item (Wi-Fi, Laundry, ...).
Property       A hostel / PG listing owned by one user.
PropertyImage  Gallery image belonging to exactly one Property.

Important notes
---------------
* ``save()`` does NOT run validators. Forms run them automatically; any other
  code (shell, scripts, services) must call ``full_clean()`` first.
* The owner is always ``settings.AUTH_USER_MODEL``. No second user model exists.
* Listing approval (``approval_status``) and availability (``is_available``)
  are deliberately two separate fields.
"""
import uuid
from pathlib import Path

import django
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models, transaction
from django.db.models import Q

# Django 5.1 renamed CheckConstraint(check=...) to condition=...; 6.0 removed check=.
_CHECK_KWARG = "condition" if django.VERSION >= (5, 1) else "check"

# --------------------------------------------------------------------------
# Image validation settings (reused by the project lead's forms)
# --------------------------------------------------------------------------
MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]

# Predefined amenity checklist, loaded with:  python manage.py seed_amenities
DEFAULT_AMENITIES = [
    ("Wi-Fi", "wifi"),
    ("Air conditioning", "air-conditioning"),
    ("Laundry", "laundry"),
    ("Food included", "food-included"),
    ("Parking", "parking"),
    ("Power backup", "power-backup"),
    ("CCTV", "cctv"),
    ("Furnished rooms", "furnished-rooms"),
]


def validate_image_size(image):
    """Reject images larger than MAX_IMAGE_SIZE_MB."""
    try:
        size = image.size
    except OSError:  # file missing from storage; nothing to measure
        return
    if size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f"Image file is too large. Maximum size is {MAX_IMAGE_SIZE_MB} MB."
        )


def property_image_upload_path(instance, filename):
    """Store files as properties/<property id>/<random>.<ext> (no filename clashes)."""
    extension = Path(filename).suffix.lower()
    folder = instance.property_id or "unassigned"
    return f"properties/{folder}/{uuid.uuid4().hex}{extension}"


# --------------------------------------------------------------------------
# Amenity
# --------------------------------------------------------------------------
class Amenity(models.Model):
    """A predefined amenity. Admins manage the list; owners only pick from it."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Stable lowercase identifier used for filtering, e.g. 'wifi'.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "amenities"

    def __str__(self):
        return self.name


# --------------------------------------------------------------------------
# Property
# --------------------------------------------------------------------------
class PropertyQuerySet(models.QuerySet):
    def public(self):
        """Listings visible to everyone: approved only (availability is separate)."""
        return self.filter(approval_status=Property.ApprovalStatus.APPROVED)

    def bookable(self):
        """Approved AND available: listings that can receive booking requests."""
        return self.public().filter(is_available=True)

    def with_amenities(self, slugs):
        """Properties having ALL of the given amenity slugs (empty list = no filter)."""
        queryset = self
        for slug in slugs:
            queryset = queryset.filter(amenities__slug=slug)
        return queryset


class Property(models.Model):
    class PropertyType(models.TextChoices):
        HOSTEL = "hostel", "Hostel"
        PG = "pg", "PG"

    class ApprovalStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class AccommodationFor(models.TextChoices):
        GIRLS = "girls", "Girls Only"
        BOYS = "boys", "Boys Only"
        ALL_GENDERS = "all", "Co-ed / All Genders"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="properties",
    )
    name = models.CharField(max_length=150)
    property_type = models.CharField(max_length=10, choices=PropertyType.choices)
    description = models.TextField()
    city = models.CharField(max_length=100)
    locality = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    postal_code = models.CharField(
        max_length=6,
        validators=[RegexValidator(r"^\d{6}$", "Enter a valid 6-digit PIN code.")],
    )
    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Rent per month in INR. Cannot be negative.",
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Whether the property is currently taking requests. "
        "Independent of approval status.",
    )
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT,
    )
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="properties")
    accommodation_for = models.CharField(
        max_length=10,
        choices=AccommodationFor.choices,
        default=AccommodationFor.ALL_GENDERS,
        help_text="Who is this property intended for? (Girls Only, Boys Only, or Co-ed / All Genders)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PropertyQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "properties"
        constraints = [
            models.CheckConstraint(
                **{_CHECK_KWARG: Q(monthly_rent__gte=0)},
                name="property_monthly_rent_gte_0",
            ),
        ]
        indexes = [
            models.Index(fields=["approval_status", "is_available"]),
            models.Index(fields=["city"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_property_type_display()}, {self.city})"

    # ---- read-only helpers (usable in templates) -------------------------
    @property
    def is_public(self):
        """True when the listing is approved (visible to everyone)."""
        return self.approval_status == self.ApprovalStatus.APPROVED

    @property
    def accepts_booking_requests(self):
        """True when the listing is approved AND marked available."""
        return self.is_public and self.is_available

    @property
    def primary_image(self):
        """Primary image, else the first gallery image, else None.

        Works with ``prefetch_related("images")`` (no extra query per property).
        """
        images = list(self.images.all())
        for image in images:
            if image.is_primary:
                return image
        return images[0] if images else None

    # ---- approval workflow ------------------------------------------------
    # Allowed transitions (nothing else is permitted):
    #   draft/rejected -> pending   (owner submits / resubmits)
    #   pending        -> approved  (administrator)
    #   pending        -> rejected  (administrator)
    def _change_status(self, allowed_from, new_status, action, validate=False):
        if self.approval_status not in allowed_from:
            raise ValidationError(
                f"Cannot {action} a listing whose status is "
                f"'{self.get_approval_status_display()}'."
            )
        if validate:
            self.full_clean()
        self.approval_status = new_status
        self.save(update_fields=["approval_status", "updated_at"])

    def submit_for_approval(self):
        """Owner action: draft or rejected -> pending. Validates all fields first."""
        self._change_status(
            (self.ApprovalStatus.DRAFT, self.ApprovalStatus.REJECTED),
            self.ApprovalStatus.PENDING,
            "submit",
            validate=True,
        )

    def approve(self):
        """Administrator action: pending -> approved."""
        self._change_status(
            (self.ApprovalStatus.PENDING,), self.ApprovalStatus.APPROVED, "approve"
        )

    def reject(self):
        """Administrator action: pending -> rejected (owner may edit and resubmit)."""
        self._change_status(
            (self.ApprovalStatus.PENDING,), self.ApprovalStatus.REJECTED, "reject"
        )


# --------------------------------------------------------------------------
# PropertyImage
# --------------------------------------------------------------------------
class PropertyImage(models.Model):
    """
    One gallery image. Gallery order is (sort_order, id): lower sort_order first,
    ties broken by upload order. At most one image per property is primary
    (enforced by a partial unique constraint).
    """

    # NOTE: this class defines a field called ``property``, which shadows the
    # built-in decorator inside the class body, so no @property is used here.
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to=property_image_upload_path,
        validators=[
            FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS),
            validate_image_size,
        ],
    )
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers appear first in the gallery."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["property"],
                condition=Q(is_primary=True),
                name="one_primary_image_per_property",
            ),
        ]

    def __str__(self):
        return f"Image #{self.pk} of {self.property.name}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # The first image uploaded for a property becomes primary automatically.
            if self._state.adding and self.property_id and not self.is_primary:
                has_images = PropertyImage.objects.filter(
                    property_id=self.property_id
                ).exists()
                if not has_images:
                    self.is_primary = True
            # Saving a new primary image demotes the previous one.
            if self.is_primary:
                PropertyImage.objects.filter(
                    property_id=self.property_id, is_primary=True
                ).exclude(pk=self.pk).update(is_primary=False)
            super().save(*args, **kwargs)
