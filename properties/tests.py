"""Tests for the Gender-Specific Accommodation feature and existing property workflows."""

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Property


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------

def _make_owner():
    return User.objects.create_user(
        "owner@example.com", "pass-12345", full_name="Owner", role=User.Role.OWNER
    )


def _base_property_data():
    return dict(
        name="Test PG",
        property_type=Property.PropertyType.PG,
        description="A comfortable and safe student accommodation.",
        city="Pune",
        locality="Kothrud",
        address="12 Lake Road",
        postal_code="411038",
        monthly_rent=9000,
    )


def _make_approved_property(owner, accommodation_for=Property.AccommodationFor.ALL_GENDERS, **kwargs):
    """Create an approved, available property for use in listing/filter tests."""
    data = _base_property_data()
    data.update(kwargs)
    data["accommodation_for"] = accommodation_for
    listing = Property.objects.create(owner=owner, **data)
    # Fast-path approval: go draft -> pending -> approved
    listing.approval_status = Property.ApprovalStatus.PENDING
    listing.save()
    listing.approve()
    return listing


# ---------------------------------------------------------------------------
# Existing workflow test (preserved)
# ---------------------------------------------------------------------------

class PropertyWorkflowTests(TestCase):
    def setUp(self):
        self.owner = _make_owner()

    def test_new_listing_can_be_submitted_then_approved(self):
        listing = Property.objects.create(owner=self.owner, **_base_property_data())
        listing.submit_for_approval()
        self.assertEqual(listing.approval_status, Property.ApprovalStatus.PENDING)
        listing.approve()
        self.assertTrue(listing.is_public)


# ---------------------------------------------------------------------------
# AccommodationFor model field tests
# ---------------------------------------------------------------------------

class AccommodationForModelTests(TestCase):
    def setUp(self):
        self.owner = _make_owner()

    def _create(self, accommodation_for=None):
        data = _base_property_data()
        if accommodation_for is not None:
            data["accommodation_for"] = accommodation_for
        return Property.objects.create(owner=self.owner, **data)

    def test_default_is_all_genders(self):
        """New properties default to ALL_GENDERS when accommodation_for is not specified."""
        listing = self._create()
        self.assertEqual(listing.accommodation_for, Property.AccommodationFor.ALL_GENDERS)
        self.assertEqual(listing.accommodation_for, "all")

    def test_create_girls_only(self):
        listing = self._create(accommodation_for=Property.AccommodationFor.GIRLS)
        self.assertEqual(listing.accommodation_for, "girls")
        self.assertEqual(listing.get_accommodation_for_display(), "Girls Only")

    def test_create_boys_only(self):
        listing = self._create(accommodation_for=Property.AccommodationFor.BOYS)
        self.assertEqual(listing.accommodation_for, "boys")
        self.assertEqual(listing.get_accommodation_for_display(), "Boys Only")

    def test_create_all_genders(self):
        listing = self._create(accommodation_for=Property.AccommodationFor.ALL_GENDERS)
        self.assertEqual(listing.accommodation_for, "all")
        self.assertEqual(listing.get_accommodation_for_display(), "Co-ed / All Genders")

    def test_accommodation_for_is_separate_from_property_type(self):
        """Both fields exist independently; neither replaces the other."""
        listing = self._create(accommodation_for=Property.AccommodationFor.GIRLS)
        self.assertEqual(listing.property_type, Property.PropertyType.PG)
        self.assertEqual(listing.accommodation_for, "girls")

    def test_edit_persists_accommodation_for(self):
        listing = self._create(accommodation_for=Property.AccommodationFor.BOYS)
        listing.accommodation_for = Property.AccommodationFor.GIRLS
        listing.save()
        listing.refresh_from_db()
        self.assertEqual(listing.accommodation_for, "girls")


# ---------------------------------------------------------------------------
# Property listing filter tests
# ---------------------------------------------------------------------------

class AccommodationFilterTests(TestCase):
    def setUp(self):
        self.owner = _make_owner()
        self.girls = _make_approved_property(self.owner, accommodation_for=Property.AccommodationFor.GIRLS, name="Girls PG")
        self.boys  = _make_approved_property(self.owner, accommodation_for=Property.AccommodationFor.BOYS,  name="Boys PG")
        self.all   = _make_approved_property(self.owner, accommodation_for=Property.AccommodationFor.ALL_GENDERS, name="Coed PG")

    def _get_list(self, params=""):
        return self.client.get(reverse("property_list") + ("?" + params if params else ""))

    def test_filter_girls_only(self):
        response = self._get_list("accommodation_for=girls")
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["properties"]]
        self.assertIn("Girls PG", names)
        self.assertNotIn("Boys PG", names)
        self.assertNotIn("Coed PG", names)

    def test_filter_boys_only(self):
        response = self._get_list("accommodation_for=boys")
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["properties"]]
        self.assertIn("Boys PG", names)
        self.assertNotIn("Girls PG", names)
        self.assertNotIn("Coed PG", names)

    def test_filter_all_genders(self):
        response = self._get_list("accommodation_for=all")
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["properties"]]
        self.assertIn("Coed PG", names)
        self.assertNotIn("Girls PG", names)
        self.assertNotIn("Boys PG", names)

    def test_no_filter_returns_all(self):
        response = self._get_list()
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["properties"]]
        self.assertIn("Girls PG", names)
        self.assertIn("Boys PG", names)
        self.assertIn("Coed PG", names)

    def test_filter_girls_combined_with_city(self):
        """Accommodation filter combines correctly with city filter."""
        response = self._get_list("accommodation_for=girls&city=Pune")
        self.assertEqual(response.status_code, 200)
        names = [p.name for p in response.context["properties"]]
        self.assertIn("Girls PG", names)
        self.assertNotIn("Boys PG", names)

    def test_unapproved_property_excluded_even_when_filtered(self):
        """An unapproved girls-only property must not appear in public search."""
        unapproved = Property.objects.create(
            owner=self.owner,
            accommodation_for=Property.AccommodationFor.GIRLS,
            **_base_property_data(),
        )
        unapproved.name = "Hidden Girls PG"
        unapproved.save()
        # Still draft — not approved
        response = self._get_list("accommodation_for=girls")
        names = [p.name for p in response.context["properties"]]
        self.assertNotIn("Hidden Girls PG", names)

    def test_invalid_accommodation_value_ignored(self):
        """A garbage value for accommodation_for should not crash and returns all results."""
        response = self._get_list("accommodation_for=xyz")
        self.assertEqual(response.status_code, 200)
        # An invalid choice is cleaned to "" and ignored, so all 3 are returned
        names = [p.name for p in response.context["properties"]]
        self.assertGreaterEqual(len(names), 3)


# ---------------------------------------------------------------------------
# Homepage shortcut test
# ---------------------------------------------------------------------------

class HomeAccommodationShortcutTests(TestCase):
    def test_girls_shortcut_link_on_home_page(self):
        """Home page must contain a link to the girls-only filter."""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "accommodation_for=girls")

    def test_girls_shortcut_redirects_to_filtered_list(self):
        """Clicking the Girls shortcut opens the listing page pre-filtered."""
        response = self.client.get(reverse("property_list") + "?accommodation_for=girls")
        self.assertEqual(response.status_code, 200)
