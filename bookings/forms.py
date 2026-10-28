"""Forms for booking requests."""

from django import forms
from django.core.exceptions import ValidationError

from .models import BookingRequest
from .services import ACTION_TO_STATUS, STATUS_PENDING, get_booking_block_reason

MAX_MESSAGE_LENGTH = 300


class BookingRequestForm(forms.ModelForm):
    """A student's request for one property, with an optional short message.

    The student and property are NOT form fields. The view supplies them, so
    they cannot be changed from the browser.
    """

    message = forms.CharField(
        required=False,
        max_length=MAX_MESSAGE_LENGTH,
        label="Message to the owner (optional)",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "maxlength": MAX_MESSAGE_LENGTH,
                "placeholder": "Introduce yourself or ask a question (optional)",
            }
        ),
    )

    class Meta:
        model = BookingRequest
        fields = ["message"]

    def __init__(self, *args, student, listing, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        self.listing = listing

    def clean_message(self):
        return self.cleaned_data["message"].strip()

    def clean(self):
        cleaned_data = super().clean()
        # One shared rule for the detail page and this form.
        reason = get_booking_block_reason(self.student, self.listing)
        if reason:
            raise ValidationError(reason)
        return cleaned_data

    def save(self):
        booking = super().save(commit=False)
        booking.student = self.student
        booking.property = self.listing
        booking.status = STATUS_PENDING
        booking.full_clean()
        booking.save()
        return booking


class BookingResponseForm(forms.Form):
    """The owner's Accept / Reject button. Only these two actions are valid."""

    action = forms.ChoiceField(choices=[(key, key.title()) for key in ACTION_TO_STATUS])

    def new_status(self):
        return ACTION_TO_STATUS[self.cleaned_data["action"]]
