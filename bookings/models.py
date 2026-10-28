"""
StayNest - booking request model.

A BookingRequest is only a request. It is NOT a payment or a guaranteed
reservation, and accepting one never changes ``Property.is_available``.

Rule ownership
--------------
Enforced here (model / database):
  * status values come from ``Status`` choices
  * one PENDING request per (student, property)  -> DB partial unique constraint
    plus an explicit check in clean() (so ModelForms that exclude ``student``
    still validate it)
  * on creation only: property must be approved + available, and the student
    cannot request their own property  -> clean()
  * allowed status transitions: cancel()/accept()/reject() only from PENDING
  * permission helpers: can_be_cancelled_by(user), can_be_responded_to_by(user)

Enforced by the project lead (views / forms):
  * the user must be logged in and have the Student / Owner role
  * calling full_clean() or a ModelForm before saving
  * calling the permission helpers before cancel()/accept()/reject()
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class BookingRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    # NOTE: this class defines a field called ``property``, which shadows the
    # built-in decorator inside the class body, so helpers here are plain methods.
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="booking_requests",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="booking_requests",
    )
    message = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "property"],
                condition=Q(status="pending"),
                name="unique_pending_request_per_student_property",
                violation_error_message=(
                    "You already have a pending request for this property."
                ),
            ),
        ]
        indexes = [models.Index(fields=["property", "status"])]

    def __str__(self):
        return f"Request #{self.pk}: {self.student_id} -> {self.property_id} ({self.status})"

    # ---- validation ------------------------------------------------------
    def clean(self):
        super().clean()
        errors = {}
        if self.property_id and self.student_id:
            # Availability rules apply only when the request is first created, so an
            # existing request stays valid if the property is later withdrawn.
            if self._state.adding:
                if not self.property.is_public:
                    errors["property"] = "This property is not publicly listed."
                elif not self.property.is_available:
                    errors["property"] = "This property is currently unavailable."
                if self.property.owner_id == self.student_id:
                    errors["student"] = "You cannot request your own property."
            if self.status == self.Status.PENDING and "property" not in errors:
                duplicate = BookingRequest.objects.filter(
                    student_id=self.student_id,
                    property_id=self.property_id,
                    status=self.Status.PENDING,
                ).exclude(pk=self.pk)
                if duplicate.exists():
                    errors["property"] = (
                        "You already have a pending request for this property."
                    )
        if errors:
            raise ValidationError(errors)

    # ---- read-only helpers (usable in templates) -------------------------
    def is_pending(self):
        return self.status == self.Status.PENDING

    def can_be_cancelled_by(self, user):
        """Only the student who made the request, and only while it is pending."""
        return bool(
            user.is_authenticated and user.pk == self.student_id and self.is_pending()
        )

    def can_be_responded_to_by(self, user):
        """Only the owner of the property, and only while the request is pending."""
        return bool(
            user.is_authenticated
            and self.property.owner_id == user.pk
            and self.is_pending()
        )

    # ---- status transitions (permission checks stay in the views) --------
    def _change_status(self, new_status, action):
        if not self.is_pending():
            raise ValidationError(
                f"Cannot {action} a request whose status is "
                f"'{self.get_status_display()}'. Only pending requests can be changed."
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])

    def cancel(self):
        self._change_status(self.Status.CANCELLED, "cancel")

    def accept(self):
        self._change_status(self.Status.ACCEPTED, "accept")

    def reject(self):
        self._change_status(self.Status.REJECTED, "reject")
