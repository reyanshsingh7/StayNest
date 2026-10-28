"""Booking workflow helpers aligned with the database models."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count

from .models import BookingRequest

STATUS_PENDING = BookingRequest.Status.PENDING
STATUS_ACCEPTED = BookingRequest.Status.ACCEPTED
STATUS_REJECTED = BookingRequest.Status.REJECTED
STATUS_CANCELLED = BookingRequest.Status.CANCELLED
ACTOR_STUDENT = "STUDENT"
ACTOR_OWNER = "OWNER"
ACTION_TO_STATUS = {"accept": STATUS_ACCEPTED, "reject": STATUS_REJECTED}


class InvalidStatusTransition(Exception):
    """A user-visible booking workflow error."""


def change_request_status(booking, new_status, actor):
    with transaction.atomic():
        current = BookingRequest.objects.select_for_update().select_related("property").get(pk=booking.pk)
        try:
            if actor == ACTOR_STUDENT:
                if not current.can_be_cancelled_by(booking.student) or new_status != STATUS_CANCELLED:
                    raise ValidationError("Only a pending request can be cancelled by its student.")
                current.cancel()
            elif actor == ACTOR_OWNER:
                if not current.can_be_responded_to_by(booking.property.owner):
                    raise ValidationError("Only the property's owner can respond to a pending request.")
                if new_status == STATUS_ACCEPTED:
                    current.accept()
                elif new_status == STATUS_REJECTED:
                    current.reject()
                else:
                    raise ValidationError("Choose Accept or Reject.")
            else:
                raise ValidationError("Invalid request action.")
        except ValidationError as error:
            raise InvalidStatusTransition(error.messages[0]) from error
    return current


def get_booking_block_reason(student, listing):
    if not student.is_student:
        return "Only student accounts can send booking requests."
    if not listing.accepts_booking_requests:
        return "This property is not currently accepting booking requests."
    if listing.owner_id == student.pk:
        return "You cannot request your own property."
    if BookingRequest.objects.filter(student=student, property=listing, status=STATUS_PENDING).exists():
        return "You already have a pending request for this property."
    return None


def count_by_status(queryset):
    counts = {"total": 0, "pending": 0, "accepted": 0, "rejected": 0, "cancelled": 0}
    for row in queryset.order_by().values("status").annotate(n=Count("id")):
        counts[row["status"]] = row["n"]
        counts["total"] += row["n"]
    return counts
