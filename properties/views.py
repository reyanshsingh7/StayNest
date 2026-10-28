"""Public property pages and owner property management."""

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import owner_required
from bookings.forms import BookingRequestForm
from bookings.models import BookingRequest
from bookings.services import STATUS_PENDING, get_booking_block_reason

from .forms import PropertyFilterForm, PropertyForm
from .models import Property, PropertyImage
from .services import (
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    attach_display_data,
    count_by_approval,
    get_amenity_labels,
    public_properties,
)


def _image_rules_context():
    """Upload limits shown next to the image field in the property form."""
    return {
        "max_images": settings.MAX_IMAGES_PER_PROPERTY,
        "max_image_size_mb": settings.MAX_IMAGE_SIZE_MB,
        "allowed_image_extensions": settings.ALLOWED_IMAGE_EXTENSIONS,
    }


# ---------------------------------------------------------------------------
# Public pages (no login needed)
# ---------------------------------------------------------------------------

def home(request):
    """Landing page: search box, a few newest available listings."""
    approved = public_properties()
    featured = approved.filter(is_available=True).order_by("-created_at", "-id")[:6]
    cities = approved.order_by("city").values_list("city", flat=True).distinct()[:12]

    context = {
        "featured_properties": attach_display_data(featured),
        "popular_cities": list(cities),
        "total_properties": approved.count(),
        "search_form": PropertyFilterForm(),
    }
    return render(request, "home.html", context)


def property_list(request):
    """Approved properties with search, filters, sorting and pagination."""
    filter_form = PropertyFilterForm(request.GET)
    filter_form.is_valid()  # fills cleaned_data (valid fields only)
    queryset = filter_form.apply(public_properties())

    paginator = Paginator(queryset, settings.PROPERTIES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Page links must keep the current filters.
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "properties": attach_display_data(page_obj.object_list),
        "page_obj": page_obj,
        "paginator": paginator,
        "is_paginated": page_obj.has_other_pages(),
        "filter_form": filter_form,
        "result_count": paginator.count,
        "query_string": params.urlencode(),
        "has_filters": any(value for key, value in request.GET.items() if key not in ("page", "sort")),
        "amenities": filter_form.fields["amenities"].queryset,
        "selected_amenities": request.GET.getlist("amenities"),
    }
    return render(request, "properties/property_list.html", context)


def property_detail(request, pk):
    """One property. Unapproved listings are visible only to their owner and staff."""
    listing = get_object_or_404(Property.objects.select_related("owner"), pk=pk)
    user = request.user

    is_owner = user.is_authenticated and listing.owner_id == user.pk
    is_public = listing.approval_status == APPROVAL_APPROVED
    if not is_public and not (is_owner or user.is_staff):
        raise Http404("Property not found.")

    images = list(PropertyImage.objects.filter(property=listing).order_by("sort_order", "id"))
    primary_image = next((i for i in images if i.is_primary), images[0] if images else None)

    is_student = user.is_authenticated and user.is_student and not user.is_staff
    booking_form = None
    booking_block_reason = None
    pending_request = None
    if is_student and is_public:
        booking_block_reason = get_booking_block_reason(user, listing)
        pending_request = BookingRequest.objects.filter(
            student=user, property=listing, status=STATUS_PENDING
        ).first()
        if booking_block_reason is None:
            booking_form = BookingRequestForm(student=user, listing=listing)

    context = {
        "property": listing,
        "owner_name": listing.owner.full_name,
        "images": images,
        "primary_image": primary_image,
        "amenity_labels": get_amenity_labels(listing),
        "is_owner": is_owner,
        "is_publicly_visible": is_public,
        "is_student": is_student,
        "can_request_booking": booking_form is not None,
        "booking_form": booking_form,
        "booking_block_reason": booking_block_reason,
        "pending_request": pending_request,
        "existing_booking": pending_request,
        "show_login_prompt": (not user.is_authenticated) and is_public and listing.is_available,
    }
    return render(request, "properties/property_detail.html", context)


# ---------------------------------------------------------------------------
# Owner pages
# ---------------------------------------------------------------------------

@owner_required
def my_properties(request):
    """All listings of the logged-in owner, with approval status."""
    own = Property.objects.filter(owner=request.user)
    status_filter = request.GET.get("status", "").lower()
    queryset = own
    if status_filter in (APPROVAL_APPROVED, APPROVAL_PENDING, APPROVAL_REJECTED):
        queryset = own.filter(approval_status=status_filter)
    else:
        status_filter = ""

    listings = attach_display_data(queryset.order_by("-created_at", "-id"))

    # Count waiting requests per property, in one query.
    waiting = (
        BookingRequest.objects.filter(property__owner=request.user, status=STATUS_PENDING)
        .order_by()
        .values("property")
        .annotate(n=Count("id"))
    )
    waiting_by_property = {row["property"]: row["n"] for row in waiting}
    for listing in listings:
        listing.pending_request_count = waiting_by_property.get(listing.pk, 0)

    context = {
        "properties": listings,
        "property_counts": count_by_approval(own),
        "status_filter": status_filter,
        "has_properties": own.exists(),
        "pending_requests_total": sum(waiting_by_property.values()),
    }
    return render(request, "properties/my_properties.html", context)


@owner_required
def property_create(request):
    """Owner adds a new listing. It starts as PENDING until an admin approves it."""
    if request.method == "POST":
        form = PropertyForm(request.POST, request.FILES, owner=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Your property was submitted. It will appear publicly after an administrator approves it.",
            )
            return redirect("my_properties")
        messages.error(request, "Please correct the errors below.")
    else:
        form = PropertyForm(owner=request.user)

    context = {"form": form, "is_edit": False, "property": None, **_image_rules_context()}
    return render(request, "properties/property_form.html", context)


@owner_required
def property_edit(request, pk):
    """Owner edits their OWN listing. Others get a 404 (existence is not revealed)."""
    listing = get_object_or_404(Property, pk=pk, owner=request.user)
    was_approved = listing.approval_status == APPROVAL_APPROVED

    if request.method == "POST":
        form = PropertyForm(request.POST, request.FILES, instance=listing, owner=request.user)
        if form.is_valid():
            form.save()
            if form.sent_for_review:
                messages.warning(
                    request,
                    "Changes saved. Because important details changed, the property was sent "
                    "for administrator approval again and is hidden from the public until approved.",
                )
            else:
                messages.success(request, "Property updated.")
            return redirect("my_properties")
        messages.error(request, "Please correct the errors below.")
    else:
        form = PropertyForm(instance=listing, owner=request.user)

    context = {
        "form": form,
        "is_edit": True,
        "property": listing,
        "was_approved": was_approved,
        "existing_images": form.existing_images,
        **_image_rules_context(),
    }
    return render(request, "properties/property_form.html", context)
