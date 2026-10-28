from django.test import TestCase

from accounts.models import User
from properties.models import Property
from .models import BookingRequest


class BookingWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.com", "pass-12345", full_name="Owner", role=User.Role.OWNER)
        self.student = User.objects.create_user("student@example.com", "pass-12345", full_name="Student", role=User.Role.STUDENT)
        self.listing = Property.objects.create(
            owner=self.owner, name="Central Hostel", property_type=Property.PropertyType.HOSTEL,
            description="Clean rooms near the university campus.", city="Delhi", locality="North Campus",
            address="1 College Road", postal_code="110007", monthly_rent=8000,
            approval_status=Property.ApprovalStatus.APPROVED,
        )

    def test_pending_request_can_be_accepted(self):
        request = BookingRequest(student=self.student, property=self.listing)
        request.full_clean()
        request.save()
        request.accept()
        self.assertEqual(request.status, BookingRequest.Status.ACCEPTED)
