from django.contrib import admin

from .models import BookingRequest


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "property", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at", "property__city")
    # student__email assumes the custom user model has an ``email`` field (see README).
    search_fields = ("student__email", "property__name", "property__city", "message")
    list_select_related = ("student", "property")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("student", "property")
    fields = ("student", "property", "message", "status", "created_at", "updated_at")
