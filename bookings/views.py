"""Booking request pages for students and owners."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.permissions import owner_required, student_required
from properties.models import Property
from properties.services import attach_display_data, public_properties

from .forms import BookingRequestForm, BookingResponseForm
from .models import BookingRequest
from .services import (
    ACTOR_OWNER,
    ACTOR_STUDENT,
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_PENDING,
    STATUS_REJECTED,
    InvalidStatusTransition,
    change_request_status,
    count_by_status,
)

VALID_STATUSES = (STATUS_PENDING, STATUS_ACCEPTED, STATUS_REJECTED, STATUS_CANCELLED)


def _form_error_messages(form):
    return [error for errors in form.errors.values() for error in errors]


def _redirect_back(request, default_url_name):
    """Go to a safe ?next= address if given, otherwise to the default page."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(default_url_name)


def _status_filter(request):
    value = request.GET.get("status", "").lower()
    return value if value in VALID_STATUSES else ""


# ---------------------------------------------------------------------------
# Student pages
# ---------------------------------------------------------------------------

@student_required
def booking_create(request, property_id):
    """Student submits a request. Only approved properties can be requested."""
    listing = get_object_or_404(public_properties(), pk=property_id)

    if request.method != "POST":
        return redirect("property_detail", pk=listing.pk)

    form = BookingRequestForm(request.POST, student=request.user, listing=listing)
    if form.is_valid():
        form.save()
        messages.success(
            request,
            f"Your request for {listing.name} was sent. The owner will review it. "
            "Note: an accepted request is not a guaranteed reservation.",
        )
        return redirect("my_requests")

    for error in _form_error_messages(form):
        messages.error(request, error)
    return redirect("property_detail", pk=listing.pk)


@student_required
def my_requests(request):
    """The student's own requests only."""
    own = BookingRequest.objects.filter(student=request.user)
    status_filter = _status_filter(request)
    queryset = own.filter(status=status_filter) if status_filter else own

    booking_requests = list(queryset.select_related("property").order_by("-created_at", "-id"))
    attach_display_data([booking.property for booking in booking_requests])

    context = {
        "booking_requests": booking_requests,
        "status_counts": count_by_status(own),
        "status_filter": status_filter,
        "has_requests": own.exists(),
    }
    return render(request, "bookings/my_requests.html", context)


@student_required
@require_POST
def booking_cancel(request, pk):
    """Student cancels one of THEIR OWN pending requests."""
    booking = get_object_or_404(BookingRequest, pk=pk, student=request.user)
    try:
        change_request_status(booking, STATUS_CANCELLED, ACTOR_STUDENT)
    except InvalidStatusTransition as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Your request was cancelled.")
    return _redirect_back(request, "my_requests")


# ---------------------------------------------------------------------------
# Owner pages
# ---------------------------------------------------------------------------

@owner_required
def owner_requests(request):
    """Requests for the owner's OWN properties only."""
    incoming = BookingRequest.objects.filter(property__owner=request.user)
    owner_properties = Property.objects.filter(owner=request.user).order_by("name")

    status_filter = _status_filter(request)
    property_filter = request.GET.get("property", "")
    queryset = incoming
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if property_filter.isdigit():
        queryset = queryset.filter(property_id=int(property_filter))
    else:
        property_filter = ""

    booking_requests = list(
        queryset.select_related("property", "student").order_by("-created_at", "-id")
    )

    context = {
        "booking_requests": booking_requests,
        "status_counts": count_by_status(incoming),
        "status_filter": status_filter,
        "property_filter": property_filter,
        "owner_properties": owner_properties,
        "has_requests": incoming.exists(),
    }
    return render(request, "bookings/owner_requests.html", context)


@owner_required
@require_POST
def booking_respond(request, pk):
    """Owner accepts or rejects a pending request for THEIR property."""
    booking = get_object_or_404(
        BookingRequest.objects.select_related("property", "student"),
        pk=pk,
        property__owner=request.user,
    )
    form = BookingResponseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid action. Please use the Accept or Reject button.")
        return _redirect_back(request, "owner_requests")

    new_status = form.new_status()
    try:
        change_request_status(booking, new_status, ACTOR_OWNER)
    except InvalidStatusTransition as error:
        messages.error(request, str(error))
    else:
        if new_status == STATUS_ACCEPTED:
            messages.success(
                request,
                "Request accepted. This is not a guaranteed reservation, and the property "
                "stays listed as available.",
            )
        else:
            messages.success(request, "Request rejected.")
    return _redirect_back(request, "owner_requests")
