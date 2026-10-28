"""Shared property query and presentation helpers."""

from django.db.models import Count

from .models import Property

APPROVAL_DRAFT = Property.ApprovalStatus.DRAFT
APPROVAL_PENDING = Property.ApprovalStatus.PENDING
APPROVAL_APPROVED = Property.ApprovalStatus.APPROVED
APPROVAL_REJECTED = Property.ApprovalStatus.REJECTED

SIGNIFICANT_FIELDS = {
    "name", "property_type", "description", "city", "locality", "address",
    "postal_code", "monthly_rent", "amenities", "accommodation_for",
}


def public_properties():
    """Approved properties, with gallery and amenities available to templates."""
    return Property.objects.public().prefetch_related("images", "amenities")


def attach_display_data(listings):
    """Evaluate a collection and attach stable template-friendly display data."""
    listings = list(listings)
    for listing in listings:
        images = list(listing.images.all())
        listing.cover_image = next((image for image in images if image.is_primary), images[0] if images else None)
        listing.amenity_labels = [amenity.name for amenity in listing.amenities.all()]
    return listings


def get_amenity_labels(listing):
    return [amenity.name for amenity in listing.amenities.all()]


def count_by_approval(queryset):
    counts = {"total": 0, "draft": 0, "approved": 0, "pending": 0, "rejected": 0}
    for row in queryset.order_by().values("approval_status").annotate(n=Count("id")):
        counts[row["approval_status"]] = row["n"]
        counts["total"] += row["n"]
    return counts
