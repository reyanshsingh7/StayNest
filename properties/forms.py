"""Property editing and discovery forms."""

import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from .models import Amenity, Property, PropertyImage
from .services import APPROVAL_PENDING, SIGNIFICANT_FIELDS


class MultipleFileInput(forms.FileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        uploads = [] if not data else (data if isinstance(data, (list, tuple)) else [data])
        cleaned = []
        for upload in uploads:
            extension = os.path.splitext(upload.name)[1].lower()
            if extension not in settings.ALLOWED_IMAGE_EXTENSIONS:
                raise ValidationError("Upload JPG, PNG, or WEBP images only.")
            if upload.size > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValidationError(f"Each image must be {settings.MAX_IMAGE_SIZE_MB} MB or smaller.")
            cleaned.append(super().clean(upload, initial))
        return cleaned


class PropertyForm(forms.ModelForm):
    images = MultipleImageField(required=False, label="Add images")
    delete_images = forms.ModelMultipleChoiceField(queryset=PropertyImage.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Property
        fields = ["name", "property_type", "accommodation_for", "description", "city", "locality", "address", "postal_code", "monthly_rent", "is_available", "amenities"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "address": forms.Textarea(attrs={"rows": 3}),
            "amenities": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.sent_for_review = False
        self.existing_images = []
        self.fields["amenities"].queryset = Amenity.objects.order_by("name")
        if self.instance.pk:
            self.existing_images = list(self.instance.images.all())
            self.fields["delete_images"].queryset = self.instance.images.all()
        else:
            del self.fields["delete_images"]

    def clean_description(self):
        value = self.cleaned_data["description"].strip()
        if len(value) < 20:
            raise ValidationError("Please write at least 20 characters describing the property.")
        return value

    def clean_monthly_rent(self):
        value = self.cleaned_data["monthly_rent"]
        if value <= 0:
            raise ValidationError("Monthly rent must be greater than zero.")
        return value

    def clean(self):
        data = super().clean()
        if len(self.existing_images) - len(data.get("delete_images") or []) + len(data.get("images") or []) > settings.MAX_IMAGES_PER_PROPERTY:
            self.add_error("images", f"A property can have at most {settings.MAX_IMAGES_PER_PROPERTY} images.")
        return data

    def save(self):
        is_new = self.instance.pk is None
        with transaction.atomic():
            listing = super().save(commit=False)
            changed = bool(set(self.changed_data) & SIGNIFICANT_FIELDS) or bool(self.cleaned_data.get("images")) or bool(self.cleaned_data.get("delete_images"))
            if is_new:
                listing.owner = self.owner
                listing.approval_status = APPROVAL_PENDING
                self.sent_for_review = True
            elif changed and listing.approval_status != APPROVAL_PENDING:
                listing.approval_status = APPROVAL_PENDING
                self.sent_for_review = True
            listing.save()
            self.save_m2m()
            for image in self.cleaned_data.get("delete_images") or []:
                image.image.delete(save=False)
                image.delete()
            highest = listing.images.aggregate(highest=Max("sort_order"))["highest"]
            for index, upload in enumerate(self.cleaned_data.get("images") or [], start=(highest if highest is not None else -1) + 1):
                PropertyImage.objects.create(property=listing, image=upload, sort_order=index)
        return listing


SORT_OPTIONS = {"newest": ["-created_at", "-id"], "rent_asc": ["monthly_rent", "-id"], "rent_desc": ["-monthly_rent", "-id"]}


class PropertyFilterForm(forms.Form):
    city = forms.CharField(required=False, max_length=100)
    locality = forms.CharField(required=False, max_length=100)
    property_type = forms.ChoiceField(required=False)
    accommodation_for = forms.ChoiceField(required=False)
    min_rent = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    max_rent = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    availability = forms.CharField(required=False)  # 'all' = include unavailable; absent = available only
    amenities = forms.ModelMultipleChoiceField(required=False, queryset=Amenity.objects.none())
    sort = forms.ChoiceField(required=False, choices=[(key, label) for key, label in (("newest", "Newest first"), ("rent_asc", "Rent: low to high"), ("rent_desc", "Rent: high to low"))])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property_type"].choices = [("", "All types")] + list(Property.PropertyType.choices)
        self.fields["accommodation_for"].choices = [("", "All accommodation types")] + list(Property.AccommodationFor.choices)
        self.fields["amenities"].queryset = Amenity.objects.order_by("name")

    def clean(self):
        data = super().clean()
        if data.get("min_rent") is not None and data.get("max_rent") is not None and data["min_rent"] > data["max_rent"]:
            self.add_error("max_rent", "Maximum rent must be higher than minimum rent.")
        return data

    def apply(self, queryset):
        data = self.cleaned_data
        for field in ("city", "locality"):
            if data.get(field): queryset = queryset.filter(**{f"{field}__icontains": data[field].strip()})
        for lookup, value in (("property_type", data.get("property_type")), ("accommodation_for", data.get("accommodation_for")), ("monthly_rent__gte", data.get("min_rent")), ("monthly_rent__lte", data.get("max_rent"))):
            if value not in (None, ""): queryset = queryset.filter(**{lookup: value})
        if data.get("availability") != "all": queryset = queryset.filter(is_available=True)
        for amenity in data.get("amenities") or []: queryset = queryset.filter(amenities=amenity)
        return queryset.distinct().order_by(*SORT_OPTIONS.get(data.get("sort") or "newest", SORT_OPTIONS["newest"]))

