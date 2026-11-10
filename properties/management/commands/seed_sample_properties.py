from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from properties.models import Amenity, Property, PropertyImage

IMAGE_DIR = Path(__file__).resolve().parents[2] / "sample_images"

P = Property.PropertyType
A = Property.AccommodationFor

OWNER_EMAIL = "sample.owner@staynest.example"
OWNER_PASSWORD = "SampleOwner123!"

# One or two listings for every category: (hostel | pg) x (girls | boys | all).
SAMPLES = [
    # ---- Hostels ----
    {
        "name": "Saraswati Girls Hostel",
        "images": ["girls-hostel-pods.jpg", "dorm-bunks-lockers.jpg"],
        "property_type": P.HOSTEL,
        "accommodation_for": A.GIRLS,
        "description": "Safe, well-lit girls hostel with a warden on site, 3 meals a day "
        "and a quiet study hall. 10 minutes' walk from the university gate.",
        "city": "Greater Noida",
        "locality": "Knowledge Park II",
        "address": "Plot 45, Knowledge Park II",
        "postal_code": "201310",
        "monthly_rent": Decimal("8500.00"),
        "amenities": ["wifi", "food-included", "cctv", "power-backup", "laundry"],
    },
    {
        "name": "Aryabhatta Boys Hostel",
        "images": ["boys-hostel-dorm.jpg", "hostel-mess-kitchen.jpg"],
        "property_type": P.HOSTEL,
        "accommodation_for": A.BOYS,
        "description": "Budget-friendly boys hostel with double and triple sharing rooms, "
        "mess facility and a common recreation room.",
        "city": "Greater Noida",
        "locality": "Alpha 1",
        "address": "B-21, Alpha 1 Commercial Belt",
        "postal_code": "201308",
        "monthly_rent": Decimal("6500.00"),
        "amenities": ["wifi", "food-included", "power-backup", "parking"],
    },
    {
        "name": "Campus Connect Co-ed Hostel",
        "images": ["coed-hostel-pods.jpg", "dorm-bunks-lockers.jpg"],
        "property_type": P.HOSTEL,
        "accommodation_for": A.ALL_GENDERS,
        "description": "Modern co-ed hostel with separate wings, biometric entry, AC rooms "
        "and a rooftop common area. Ideal for students and interns.",
        "city": "Noida",
        "locality": "Sector 62",
        "address": "C-14, Sector 62",
        "postal_code": "201309",
        "monthly_rent": Decimal("11000.00"),
        "amenities": ["wifi", "air-conditioning", "cctv", "furnished-rooms", "laundry", "power-backup"],
    },
    # ---- PGs ----
    {
        "name": "Lakshmi Girls PG",
        "images": ["ac-room-attached-bath.jpg"],
        "property_type": P.PG,
        "accommodation_for": A.GIRLS,
        "description": "Homely PG for girls run by a family on the premises. Fully furnished "
        "single and double rooms with home-style meals.",
        "city": "Delhi",
        "locality": "Mukherjee Nagar",
        "address": "House 112, Gali No. 4, Mukherjee Nagar",
        "postal_code": "110009",
        "monthly_rent": Decimal("9500.00"),
        "amenities": ["wifi", "food-included", "furnished-rooms", "cctv", "laundry"],
    },
    {
        "name": "Sunrise Boys PG",
        "images": ["single-room-desk.jpg"],
        "property_type": P.PG,
        "accommodation_for": A.BOYS,
        "description": "Clean, well-ventilated rooms for boys close to the metro station. "
        "Attached bathrooms, daily housekeeping and power backup.",
        "city": "Delhi",
        "locality": "Laxmi Nagar",
        "address": "D-7, Vikas Marg, Laxmi Nagar",
        "postal_code": "110092",
        "monthly_rent": Decimal("7500.00"),
        "amenities": ["wifi", "power-backup", "furnished-rooms", "parking"],
    },
    {
        "name": "UrbanNest Co-ed PG",
        "images": ["ac-room-attached-bath.jpg", "single-room-desk.jpg"],
        "property_type": P.PG,
        "accommodation_for": A.ALL_GENDERS,
        "description": "Premium co-ed PG for students and working professionals with AC "
        "rooms, high-speed Wi-Fi and a shared kitchen and lounge.",
        "city": "Gurugram",
        "locality": "Sector 14",
        "address": "H-33, Sector 14",
        "postal_code": "122001",
        "monthly_rent": Decimal("13500.00"),
        "amenities": ["wifi", "air-conditioning", "furnished-rooms", "laundry", "cctv", "parking"],
    },
]


class Command(BaseCommand):
    help = (
        "Create sample hostels and PGs (girls / boys / co-ed) with an approved status. "
        "Safe to run repeatedly: existing samples are not duplicated."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_amenities", verbosity=0)

        User = get_user_model()
        owner, owner_created = User.objects.get_or_create(
            email=OWNER_EMAIL,
            defaults={"full_name": "Sample Owner", "role": User.Role.OWNER},
        )
        if owner_created:
            owner.set_password(OWNER_PASSWORD)
            owner.save()

        created = 0
        for data in SAMPLES:
            data = dict(data)
            amenity_slugs = data.pop("amenities")
            image_files = data.pop("images", [])
            listing, was_created = Property.objects.get_or_create(
                owner=owner,
                name=data["name"],
                defaults={**data, "approval_status": Property.ApprovalStatus.APPROVED},
            )
            if was_created:
                listing.full_clean()
                listing.amenities.set(Amenity.objects.filter(slug__in=amenity_slugs))
                created += 1

            # Attach photos to new AND already-seeded listings that have none yet.
            if image_files and not listing.images.exists():
                self._attach_images(listing, image_files)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sample properties: {created} created, {len(SAMPLES) - created} already present."
            )
        )
        if owner_created:
            self.stdout.write(f"Sample owner login: {OWNER_EMAIL} / {OWNER_PASSWORD}")

    def _attach_images(self, listing, filenames):
        """First file becomes the primary image (the model does this automatically)."""
        for order, filename in enumerate(filenames):
            path = IMAGE_DIR / filename
            if not path.exists():
                self.stdout.write(self.style.WARNING(f"Missing sample image: {path}"))
                continue
            image = PropertyImage(property=listing, sort_order=order)
            image.image.save(filename, ContentFile(path.read_bytes()), save=False)
            image.save()
