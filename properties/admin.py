from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import Amenity, Property, PropertyImage

STATUS_COLOURS = {
    Property.ApprovalStatus.DRAFT: "#6b7280",
    Property.ApprovalStatus.PENDING: "#b45309",
    Property.ApprovalStatus.APPROVED: "#15803d",
    Property.ApprovalStatus.REJECTED: "#b91c1c",
}


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1
    fields = ("image", "is_primary", "sort_order")
    ordering = ("sort_order", "id")


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "property_type",
        "accommodation_for",
        "city",
        "locality",
        "monthly_rent",
        "owner",
        "approval_badge",
        "is_available",
        "created_at",
    )
    list_filter = ("approval_status", "property_type", "accommodation_for", "is_available", "city", "amenities")
    # owner__email assumes the custom user model has an ``email`` field (see README).
    search_fields = ("name", "city", "locality", "address", "postal_code", "owner__email")
    list_select_related = ("owner",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("amenities",)
    inlines = [PropertyImageInline]
    actions = ["approve_selected", "reject_selected"]
    fieldsets = (
        ("Listing", {"fields": ("name", "property_type", "accommodation_for", "description", "owner")}),
        ("Location", {"fields": ("city", "locality", "address", "postal_code")}),
        ("Pricing and availability", {"fields": ("monthly_rent", "is_available")}),
        ("Amenities", {"fields": ("amenities",)}),
        ("Review", {"fields": ("approval_status",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Approval", ordering="approval_status")
    def approval_badge(self, obj):
        return format_html(
            '<strong style="color:{};">{}</strong>',
            STATUS_COLOURS.get(obj.approval_status, "#000000"),
            obj.get_approval_status_display(),
        )

    def _review(self, request, queryset, method_name, done_text):
        done = skipped = 0
        for listing in queryset:
            try:
                getattr(listing, method_name)()
                done += 1
            except ValidationError:
                skipped += 1
        if done:
            self.message_user(request, f"{done} listing(s) {done_text}.", messages.SUCCESS)
        if skipped:
            self.message_user(
                request,
                f"{skipped} listing(s) skipped: only 'Pending Approval' listings can be reviewed.",
                messages.WARNING,
            )

    @admin.action(description="Approve selected listings (pending only)")
    def approve_selected(self, request, queryset):
        self._review(request, queryset, "approve", "approved")

    @admin.action(description="Reject selected listings (pending only)")
    def reject_selected(self, request, queryset):
        self._review(request, queryset, "reject", "rejected")
